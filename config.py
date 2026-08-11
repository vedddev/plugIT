from providers.models import DEFAULT_MODELS

ROUTING_POLICY = {
    # A route must name a model owned by its provider.  ModelSelector also
    # validates this against the registered provider catalog.
    "coding": {"provider": "groq", "model": DEFAULT_MODELS["groq"]},
    "translation": {"provider": "groq", "model": DEFAULT_MODELS["groq"]},
    "summarization": {"provider": "groq", "model": DEFAULT_MODELS["groq"]},
    "general": {"provider": "groq", "model": DEFAULT_MODELS["groq"]},
    "vision": {"provider": "gemini", "model": DEFAULT_MODELS["gemini"]},
    "image_generation": {"provider": "gemini", "model": DEFAULT_MODELS["gemini"]},
}
