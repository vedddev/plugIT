import json
import time
import uuid

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse

from api.auth import require_api_key
from api.rate_limit import limiter
from api.dependencies import gateway, usage_tracker
from api.openai_schemas import ChatCompletionRequest
from api.quota import check_quota
from router.exceptions import AllProvidersFailedError, ModelNotFoundError
from api.errors import error_body


router = APIRouter(
    prefix="/v1",
    tags=["OpenAI Compatible"],
)


@router.get("/models")
def models(
    response: Response,
    api_key: dict = Depends(require_api_key),
):
    _apply_rate_limit(response, api_key["id"])
    data = []

    for provider in gateway.registry.providers.values():

        for model in provider.list_models():

            data.append(
                {
                    "id": model,
                    "object": "model",
                    "owned_by": provider.name,
                }
            )

    return {
        "object": "list",
        "data": data,
    }

@router.post("/chat/completions")
def chat(
    request: ChatCompletionRequest,
    response: Response,
    api_key: dict = Depends(require_api_key),
):
    _apply_rate_limit(response, api_key["id"])
    check_quota(api_key["id"], usage_tracker)

    system_prompt, prompt = _request_prompt(request)
    # ``auto`` is a gateway-level virtual model, not a provider model.
    model = None if request.model.strip().lower() == "auto" else request.model

    generation = _generation_options(request)
    if request.stream:
        return _stream_response(prompt, system_prompt, model, api_key, generation)

    try:
        print("========================================")
        print("[RIM] Requested model:", request.model)
        print("[RIM] Model passed to gateway:", model)
        print("[RIM] API key:", api_key["id"] if isinstance(api_key, dict) else api_key)
        print("========================================")
        response = gateway.chat(
            prompt=prompt.strip(),
            system_prompt=system_prompt,
            model=model,
            api_key_id=api_key["id"],
            user_id=api_key["user_id"],
            generation=generation,
        )

        usage_tracker.record(
            api_key=api_key["id"],
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            total_tokens=response.usage.total_tokens,
            cost=response.cost,
            success=True,
        )

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": response.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.total_tokens,
            },
        }

    except ModelNotFoundError as error:
        usage_tracker.record(api_key=api_key["id"], success=False)
        raise

    except AllProvidersFailedError:
        usage_tracker.record(api_key=api_key["id"], success=False)
        raise
    except Exception:
        usage_tracker.record(
            api_key=api_key["id"],
            success=False,
        )
        raise
@router.post("/chat/completions/stream")
def stream(
    request: ChatCompletionRequest,
    response: Response,
    api_key: dict = Depends(require_api_key),
):
    _apply_rate_limit(response, api_key["id"])
    check_quota(api_key["id"], usage_tracker)

    system_prompt, prompt = _request_prompt(request)
    model = None if request.model.strip().lower() == "auto" else request.model
    return _stream_response(prompt, system_prompt, model, api_key, _generation_options(request))


def _request_prompt(request: ChatCompletionRequest) -> tuple[str | None, str]:
    """Translate the supported OpenAI message roles into gateway inputs."""
    system_prompts = [message.content for message in request.messages if message.role == "system"]
    prompt = "\n".join(message.content for message in request.messages if message.role == "user")
    return ("\n".join(system_prompts) or None), prompt


def _generation_options(request: ChatCompletionRequest) -> dict:
    return {key: value for key, value in {
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }.items() if value is not None}


def _apply_rate_limit(response: Response, api_key_id: str) -> None:
    result = limiter.check(api_key_id)
    response.headers["X-RateLimit-Limit"] = str(result["limit"])
    response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
    response.headers["X-RateLimit-Reset"] = str(result["reset"])


def _sse(payload: dict | str) -> str:
    data = payload if isinstance(payload, str) else json.dumps(payload, separators=(",", ":"))
    return f"data: {data}\n\n"


def _stream_response(prompt: str, system_prompt: str | None, model: str | None, api_key: dict, generation: dict | None = None):
    """Preflight before returning StreamingResponse so failures retain HTTP status.

    A provider may be retried/fallen back only here, before any completion bytes
    are emitted.  A later provider failure terminates this SSE response and is
    never switched to another provider, which would mix two completions.
    """
    print("[Stream] Request received")
    try:
        prepared = gateway.prepare_stream(prompt=prompt, system_prompt=system_prompt, model=model, api_key_id=api_key["id"], user_id=api_key["user_id"], generation=generation)
    except ModelNotFoundError as error:
        usage_tracker.record(api_key=api_key["id"], success=False)
        raise
    except AllProvidersFailedError:
        usage_tracker.record(api_key=api_key["id"], success=False)
        raise
    except Exception:
        usage_tracker.record(api_key=api_key["id"], success=False)
        raise

    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())
    base = {"id": completion_id, "object": "chat.completion.chunk", "created": created, "model": prepared.model}

    def chunk(delta: dict, finish_reason: str | None = None) -> dict:
        return {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]}

    def generate():
        success = None
        try:
            yield _sse(chunk({"role": "assistant", "content": ""}))
            yield _sse(chunk({"content": prepared.first_chunk}))
            for text in prepared.iterator:
                yield _sse(chunk({"content": text}))
            success = True
            yield _sse(chunk({}, "stop"))
            yield _sse("[DONE]")
        except Exception:
            # Headers/content may already have been sent, so an HTTP JSON error
            # is no longer possible. Do not fall back after visible content.
            success = False
            print("[Stream] Stream failed after it started; not falling back")
            yield _sse(error_body("Provider failed while streaming.", "server_error", "provider_error"))
            yield _sse("[DONE]")
        finally:
            prepared.close()
            gateway.finish_stream(prepared, prompt, success)
            if success is not None:
                usage_tracker.record(api_key=api_key["id"], success=success)

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@router.get("/usage")
def usage(
    api_key: dict = Depends(require_api_key),
):
    return usage_tracker.get(api_key["id"])
