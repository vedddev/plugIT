import time
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse

from api.auth import verify_api_key
from api.rate_limit import rate_limit
from api.dependencies import gateway, usage_tracker
from api.openai_schemas import ChatCompletionRequest
from api.quota import check_quota
from router.exceptions import ModelNotFoundError


router = APIRouter(
    prefix="/v1",
    tags=["OpenAI Compatible"],
)


@router.get("/models")
def models(
    user: str = Depends(rate_limit),
):
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
    api_key: str = Depends(rate_limit),
):
    check_quota(api_key, usage_tracker)

    system_prompt = None
    prompt = ""

    for message in request.messages:
        if message.role == "system":
            system_prompt = message.content

        elif message.role == "user":
            prompt += message.content + "\n"

    # "auto" means SmartLLM chooses the model from the prompt
    model = request.model

    if model == "auto":
        model = None

    try:
        response = gateway.chat(
            prompt=prompt.strip(),
            system_prompt=system_prompt,
            model=model,
        )

        usage_tracker.record(
            api_key=api_key,
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
        usage_tracker.record(api_key=api_key, success=False)
        return JSONResponse(status_code=404, content={'error': {'message': str(error), 'type': 'invalid_request_error', 'param': 'model', 'code': 'model_not_found'}})

    except Exception:
        usage_tracker.record(
            api_key=api_key,
            success=False,
        )
        raise



@router.post("/chat/completions/stream")
def stream(
    request: ChatCompletionRequest,
    api_key: str = Depends(rate_limit),
):
    check_quota(api_key, usage_tracker)

    system_prompt = None
    prompt = ""

    for message in request.messages:
        if message.role == "system":
            system_prompt = message.content

        elif message.role == "user":
            prompt += message.content + "\n"

    model = request.model

    if model == "auto":
        model = None

    def generate():
        for chunk in gateway.stream(
            prompt=prompt.strip(),
            system_prompt=system_prompt,
            model=model,
        ):
            yield f"data: {chunk}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
@router.get("/usage")
def usage(
    api_key: str = Depends(verify_api_key),
):
    return usage_tracker.get(api_key)