from google import genai

client = genai.Client(api_key="")

for model in client.models.list():
    print(model.name)