import time
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.dependencies import gateway
from api.openai_schemas import (
    ChatCompletionRequest,
)

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])

@router.get("/models")
def models():

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
def chat(request: ChatCompletionRequest):

    system_prompt = None
    prompt = ""

    for message in request.messages:

        if message.role == "system":
            system_prompt = message.content

        elif message.role == "user":
            prompt += message.content + "\n"

    response = gateway.chat(
        prompt=prompt.strip(),
        system_prompt=system_prompt,
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
@router.post("/chat/completions/stream")
def stream(request: ChatCompletionRequest):

    system_prompt = None
    prompt = ""

    for message in request.messages:

        if message.role == "system":
            system_prompt = message.content

        elif message.role == "user":
            prompt += message.content + "\n"

    def generate():

        for chunk in gateway.stream(
            prompt=prompt.strip(),
            system_prompt=system_prompt,
        ):
            yield f"data: {chunk}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )