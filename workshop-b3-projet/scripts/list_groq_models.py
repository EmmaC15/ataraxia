"""
Liste les modèles réellement accessibles avec votre clé API Groq.
Usage : python scripts/list_groq_models.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"
headers = {"Authorization": f"Bearer {api_key}"}

response = requests.get(url, headers=headers)
data = response.json()

print("Modèles accessibles avec votre clé :\n")
for model in data.get("data", []):
    print(f"- {model['id']}")