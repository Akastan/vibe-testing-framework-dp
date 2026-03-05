import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

print("=== Dostupné modely pro tvůj API klíč ===")
# Získáme všechny modely
for model in client.models.list():
    # Vypíšeme jen ty, které umí generovat obsah (a ne jen např. embeddings)
    if 'generateContent' in model.supported_actions:
        print(model.name)