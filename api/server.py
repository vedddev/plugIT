from contextlib import asynccontextmanager
from pathlib import Path

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.dependencies import gateway
from api.schemas import ChatRequest, ChatResponseModel
from fastapi.responses import StreamingResponse
from api.openai_routes import router as openai_router
from api.admin_routes import router as admin_router
from api.dashboard_routes import router as dashboard_router
from api.auth_routes import router as auth_router
from api.errors import register_exception_handlers
from database import initialize_database


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize the application database before serving requests."""
    initialize_database()
    gateway.tracker.enable_database()
    yield

app = FastAPI(
    title="Rim",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("RIM_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(openai_router)
app.include_router(admin_router)
app.include_router(dashboard_router)
app.include_router(auth_router)
register_exception_handlers(app)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/dashboard", StaticFiles(directory=FRONTEND_DIR, html=True), name="dashboard-ui")

@app.get("/")
def home():
    return {
        "message": "Rim API",
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
    


