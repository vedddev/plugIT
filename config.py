from providers.models import DEFAULT_MODELS

ROUTING_POLICY = {
    "coding": {"provider": "groq", "model": DEFAULT_MODELS["gemini"]},
    "translation": {"provider": "groq", "model": DEFAULT_MODELS["gemini"]},
    "summarization": {"provider": "groq", "model": DEFAULT_MODELS["gemini"]},
    "general": {"provider": "groq", "model": DEFAULT_MODELS["gemini"]},
    "vision": {"provider": "gemini", "model": DEFAULT_MODELS["gemini"]},
    "image_generation": {"provider": "gemini", "model": DEFAULT_MODELS["gemini"]},
}
