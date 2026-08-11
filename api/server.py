from fastapi import FastAPI

from api.dependencies import gateway
from api.schemas import ChatRequest, ChatResponseModel
from fastapi.responses import StreamingResponse
from api.openai_routes import router as openai_router
from api.errors import register_exception_handlers

app = FastAPI(
    title="SmartLLM",
    version="1.0.0",
)

app.include_router(openai_router)
register_exception_handlers(app)

@app.get("/")
def home():
    return {
        "message": "SmartLLM API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.get("/providers")
def providers():
    return gateway.registry.list()


@app.post("/chat", response_model=ChatResponseModel)
def chat(request: ChatRequest):

    response = gateway.chat(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
    )

    return {
        "provider": response.provider,
        "model": response.model,
        "content": response.content,

        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.total_tokens,

        "latency_ms": response.latency_ms,
        "cost": response.cost,
        "cached": response.metadata.get("cached", False),
    }

@app.get('/models')
def models():
    result = {}

    for provider in gateway.registry.providers.values():
        result[provider.name] = provider.list_models()

    return result

@app.get("/metrics")
def metrics():
    return {
        "status": "coming soon"
    }


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):

    def generate():
        for chunk in gateway.stream(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
        ):
            yield f"data: {chunk}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
    


