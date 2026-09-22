"""
Client minimal pour l'API World Labs (Marble).

Fonction principale à utiliser dans le pipeline : generer_monde(description)
qui renvoie l'URL VR du monde généré, ou None en cas d'échec/timeout.
"""

import time
import requests

from marble.config import API_KEY, BASE_URL, MODEL, POLL_INTERVAL_SECONDS, POLL_TIMEOUT_SECONDS


def _headers():
    return {
        "Content-Type": "application/json",
        "WLT-Api-Key": API_KEY,
    }


def lancer_generation(description: str, display_name: str = "workshop-b3-scene") -> str:
    """
    Démarre une génération de monde à partir d'une description texte.
    Renvoie l'operation_id à utiliser pour le polling.
    """
    url = f"{BASE_URL}/marble/v1/worlds:generate"
    payload = {
        "display_name": display_name,
        "model": MODEL,
        "world_prompt": {
            "type": "text",
            "text_prompt": description,
        },
    }

    response = requests.post(url, json=payload, headers=_headers(), timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["operation_id"]


def attendre_operation(operation_id: str) -> dict:
    """
    Interroge le statut de l'opération jusqu'à ce qu'elle soit terminée,
    ou jusqu'au timeout. Renvoie la réponse complète de l'opération.
    """
    url = f"{BASE_URL}/marble/v1/operations/{operation_id}"
    elapsed = 0

    while elapsed < POLL_TIMEOUT_SECONDS:
        response = requests.get(url, headers=_headers(), timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get("done"):
            return data

        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS

    raise TimeoutError(f"Génération Marble non terminée après {POLL_TIMEOUT_SECONDS}s")


def generer_monde(description: str) -> str | None:
    """
    Fonction à appeler depuis le pipeline principal.
    Lance la génération, attend le résultat, renvoie l'URL VR du monde
    (ou None si erreur/timeout — le pipeline doit gérer ce cas).
    """
    try:
        operation_id = lancer_generation(description)
        resultat = attendre_operation(operation_id)

        if resultat.get("error"):
            print(f"[Marble] Erreur de génération : {resultat['error']}")
            return None

        world = resultat.get("response", {})
        url = world.get("world_marble_url")

        if not url:
            # Ne devrait normalement pas arriver — on affiche tout pour comprendre.
            print("[Marble] Pas d'URL trouvée dans la réponse. Réponse complète :")
            print(resultat)
            return None

        return url

    except requests.HTTPError as e:
        # Cas fréquent : 402 = crédits insuffisants, 401/403 = clé invalide.
        print(f"[Marble] Erreur HTTP {e.response.status_code} : {e.response.text}")
        return None

    except (requests.RequestException, TimeoutError) as e:
        print(f"[Marble] Échec génération (réseau/timeout) : {e}")
        return None

    except Exception as e:
        # Filet de sécurité : on ne veut plus jamais d'échec silencieux.
        print(f"[Marble] Erreur inattendue ({type(e).__name__}) : {e}")
        return None