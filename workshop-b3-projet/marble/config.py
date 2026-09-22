import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("WLT_API_KEY")
BASE_URL = "https://api.worldlabs.ai"

# Modèle rapide pour les tests et la démo live (30-45 sec environ).
# Passer à "Marble 0.1-plus" seulement si vous testez la qualité en dehors
# du live, car c'est nettement plus lent.
MODEL = "marble-1.0-draft"

# Intervalle et durée max de polling pendant l'attente de génération
POLL_INTERVAL_SECONDS = 3
POLL_TIMEOUT_SECONDS = 90