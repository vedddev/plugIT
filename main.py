import requests
import os
from dotenv import load_dotenv
load_dotenv()
RIM_URL = "http://127.0.0.1:8000/v1/chat/completions"

RIM_KEY = "sk-smartllm-PRVzro0VdGNjVS5fa8SnJX5qNHzirl97ZInfur-amqo"

body = {
    "model": "llama-3.1-8b-instant",
    "messages": [
        {
            "role": "user",
            "content": "write code of two sum in python"
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