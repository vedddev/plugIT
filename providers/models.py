"""Canonical model catalog used by providers, routing, and fallback."""

PROVIDER_MODELS = {
    "groq": ("llama-3.3-70b-versatile", "llama-3.1-8b-instant", "qwen/qwen3-32b", "deepseek-r1-distill-llama-70b"),
    "gemini": (
        "gemini-3.6-flash",
        "gemini-flash-latest", "gemini-flash-lite-latest", "gemini-pro-latest",
        "gemini-3-flash-preview", "gemini-3.1-pro-preview",
        "gemini-3.1-pro-preview-customtools", "gemini-3.1-flash-lite-preview",
        "gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.5-flash-lite",
        "gemini-omni-flash-preview", "gemma-4-26b-a4b-it", "gemma-4-31b-it",
    ),
    "openai": ("gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4o"),
}
DEFAULT_MODELS = {provider: models[0] for provider, models in PROVIDER_MODELS.items()}
