from dotenv import load_dotenv
import os

from api.gateway import SmartLLM
from providers.groq import GroqProvider
from providers.registry import ProviderRegistry
from providers.gemini import GeminiProvider
import redis

load_dotenv()


def main():

    # Register Providers

    registry = ProviderRegistry()

    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key=os.getenv("GEMINI_API_KEY")
    if groq_key:
        registry.register(
            GroqProvider(api_key=groq_key)
        )
    if gemini_key:
        registry.register(
            GeminiProvider(api_key=gemini_key)
        )
    print("Registered Providers:", registry.list())
    print("-" * 50)

    # Create Gateway

    gateway = SmartLLM(registry)

    # User Prompt
    prompt = "create image of happy face"
    response = gateway.chat(prompt)

    # Output

    print("\n========== SmartLLM ==========")

    print(f"Prompt      : {prompt}")
    print(f"Provider    : {response.provider}")
    print(f"Model       : {response.model}")
    print(f"Latency     : {response.latency_ms:.2f} ms")
    print(f"Input Tokens: {response.usage.input_tokens}")
    print(f"Output      : {response.usage.output_tokens}")
    print(f"Total Tokens: {response.usage.total_tokens}")
    print(f"Cost        : ${response.cost}")
    print("Cached     :", response.metadata.get("cached", False))
    print("\n========== Response ==========\n")
    print(response.content)


if __name__ == "__main__":
    main()