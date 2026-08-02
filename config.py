# config.py

ROUTING_POLICY = {
    "coding": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile"
    },

    "translation": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant"
    },

    "summarization": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant"
    },

    "general": {
        "provider": "groq",
        "model": "llama-3.1-8b-instant"
    },

    "vision": {
        "provider": "gemini",
        "model": "models/gemini-3.6-flash"
    },

    "image_generation": {
        "provider": "gemini",
        "model": "models/gemini-3.1-flash-lite-image"
    }
}