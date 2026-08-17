import requests
import os
from dotenv import load_dotenv
load_dotenv()
RIM_URL = "http://127.0.0.1:8000/v1/chat/completions"

RIM_KEY = os.getenv("SMARTLLM_ADMIN_KEY")

body = {
    "model": "llama-3.3-70b-versatile",
    "messages": [
        {
            "role": "user",
            "content": "Hello my friend."
        }
    ]
}

headers = {
    "Authorization": f"Bearer {RIM_KEY}",
    "Content-Type": "application/json",
}

print("Sending request to RIM...")

response = requests.post(
    RIM_URL,
    headers=headers,
    json=body,
    timeout=120,
)

print("HTTP status:", response.status_code)

if response.ok:
    data = response.json()

    print("\n========== SmartLLM/RIM ==========")
    print("Request successful")
    print("Model:", data.get("model"))

    content = data["choices"][0]["message"]["content"]
    print("\nResponse:")
    print(content)

    print("\nUsage:")
    print(data.get("usage"))

else:
    print("\nRequest failed:")
    print(response.text)