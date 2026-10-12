import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("AI_API_KEY")

if not api_key:
    raise Exception("AI_API_KEY is not set")

print("GEMINI_API_KEY loaded successfully")
print("Key length:", len(api_key))

client = genai.Client(api_key=api_key)

interaction = client.interactions.create(
    model="gemini-3.8-flash",
    input="Reply with exactly: Gemini API is working"
)

print("\nGemini response:")
print(interaction.output_text)