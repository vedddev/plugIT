import os; 
from dotenv import load_dotenv; 
from google import genai; load_dotenv();
client=genai.Client(api_key=os.environ['GEMINI_API_KEY']); 
response=client.models.generate_content(model='models/gemini-3.6-flash', contents='Reply with exactly: Gemini API key works'); 
print(response.text)