"""
Sélection du périphérique audio d'entrée (micro).

Logique : on cherche en priorité un micro dont le nom contient un mot-clé
lié au casque VR (à adapter selon votre modèle exact — vérifiez le nom
exact affiché par lister_peripheriques() ci-dessous). Si aucun micro de
casque n'est détecté, on retombe sur le micro par défaut du PC.
"""

import sounddevice as sd

# À adapter selon votre casque une fois que vous aurez vu le nom exact
# affiché par lister_peripheriques() (ex: "Oculus", "Quest", "Vive", "HTC")
MOTS_CLES_CASQUE = ["oculus", "quest", "vive", "htc", "valve", "pico", "vr"]


def lister_peripheriques():
    """Affiche tous les périphériques audio d'entrée disponibles avec leur index."""
    peripheriques = sd.query_devices()
    entrees = []
    for i, p in enumerate(peripheriques):
        if p["max_input_channels"] > 0:
            entrees.append((i, p["name"]))
            print(f"[{i}] {p['name']} (entrées: {p['max_input_channels']})")
    return entrees


def trouver_micro_casque():
    """
    Cherche un périphérique d'entrée dont le nom contient un mot-clé
    de casque VR. Renvoie son index, ou None si rien trouvé.
    """
    peripheriques = sd.query_devices()
    for i, p in enumerate(peripheriques):
        if p["max_input_channels"] > 0:
            nom = p["name"].lower()
            if any(mot in nom for mot in MOTS_CLES_CASQUE):
                return i
    return None


def obtenir_index_micro(forcer_pc: bool = False) -> int | None:
    """
    Renvoie l'index du micro à utiliser.
    - Par défaut : priorité au micro du casque s'il est détecté.
    - forcer_pc=True : ignore le casque et utilise le micro par défaut du PC
      (utile en secours pendant la démo si le casque a un souci).
    """
    if not forcer_pc:
        index_casque = trouver_micro_casque()
        if index_casque is not None:
            print(f"Micro casque détecté (index {index_casque}), utilisation prioritaire.")
            return index_casque

    print("Utilisation du micro par défaut du PC.")
    return None  # None = laisser sounddevice utiliser le micro par défaut du système


if __name__ == "__main__":
    print("Périphériques d'entrée audio disponibles :\n")
    lister_peripheriques()
    print()
    index = obtenir_index_micro()
    print(f"\nIndex sélectionné pour l'enregistrement : {index}")