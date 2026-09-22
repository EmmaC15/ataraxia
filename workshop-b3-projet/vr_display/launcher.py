"""
Ouvre une URL (le monde Marble généré) dans le navigateur par défaut.
Sur le casque VR, si le navigateur du casque est bien celui utilisé pour
la démo, ça suffit à afficher le monde directement dedans.
"""

import webbrowser


def ouvrir_dans_navigateur(url: str) -> bool:
    """Ouvre l'URL dans le navigateur par défaut. Renvoie True si ça a réussi."""
    if not url:
        print("[VR] Aucune URL à ouvrir.")
        return False

    print(f"[VR] Ouverture du monde : {url}")
    return webbrowser.open(url)