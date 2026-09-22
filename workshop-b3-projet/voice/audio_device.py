import sounddevice as sd

def lister_micros():
    peripheriques = sd.query_devices()
    for i, p in enumerate(peripheriques):
        if p["max_input_channels"] > 0:
            print(f"{i}: {p['name']}")


def trouver_micro(mot_cle: str) -> int | None:
    """Cherche un micro dont le nom contient mot_cle (insensible a la casse).
    Retourne son index, ou None si non trouve."""
    peripheriques = sd.query_devices()
    for i, p in enumerate(peripheriques):
        if p["max_input_channels"] > 0 and mot_cle.lower() in p["name"].lower():
            return i
    return None

def selectionner_micro() -> int:
    """Essaie de trouver le micro du casque VR ; sinon utilise le micro du PC."""
    index_casque = trouver_micro("Quest") or trouver_micro("Oculus")
    if index_casque is not None:
        print("Micro casque VR detecte, utilisation.")
        return index_casque

    index_pc = trouver_micro("Realtek")
    print("Micro casque non detecte, utilisation du micro PC.")
    return index_pc