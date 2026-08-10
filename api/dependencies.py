import os

from dotenv import load_dotenv

from api.gateway import SmartLLM

from providers.registry import ProviderRegistry
from providers.groq import GroqProvider
from providers.gemini import GeminiProvider
from providers.openai import OpenAIProvider
from analytics.usage import UsageTracker

load_dotenv()

registry = ProviderRegistry()

groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    registry.register(GroqProvider(api_key=groq_key))

# openai_key = os.getenv("OPENAI_API_KEY")
# if openai_key:
#     registry.register(OpenAIProvider(api_key=openai_key))

gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    registry.register(GeminiProvider(api_key=gemini_key))

gateway = SmartLLM(registry)
usage_tracker = UsageTracker()
