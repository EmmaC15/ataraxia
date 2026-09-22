import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WLT_API_KEY")
BASE_URL = "https://api.worldlabs.ai"

# Modèle rapide pour les tests et la démo live (30-45 sec environ).
# Nom confirmé par un vrai appel API (22/09/2026) : "marble-1.0-draft"
MODEL = "marble-1.0-draft"

# Intervalle et durée max de polling pendant l'attente de génération
POLL_INTERVAL_SECONDS = 3
POLL_TIMEOUT_SECONDS = 90