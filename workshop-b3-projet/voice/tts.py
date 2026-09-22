"""
Synthèse vocale (TTS) pour Ataraxia, en français, via gTTS (Google
Text-to-Speech). Remplace Orpheus (Groq), qui est anglais uniquement et
prononce le français avec un accent anglais.

Fonction principale à utiliser dans le pipeline : parler(texte)
"""

import os
import tempfile
import uuid
from gtts import gTTS
from playsound import playsound


def synthetiser(texte: str, chemin_sortie: str | None = None) -> str | None:
    """
    Génère un fichier audio (mp3) à partir du texte donné, en français.
    Renvoie le chemin du fichier, ou None en cas d'échec.
    """
    if not texte:
        return None

    if chemin_sortie is None:
        # Nom de fichier unique à chaque appel : sur Windows, playsound peut
        # garder le fichier précédent verrouillé une fraction de seconde
        # après la lecture, ce qui bloquerait une réécriture au même chemin.
        nom_fichier = f"ataraxia_reponse_{uuid.uuid4().hex}.mp3"
        chemin_sortie = os.path.join(tempfile.gettempdir(), nom_fichier)

    try:
        tts = gTTS(text=texte, lang="fr")
        tts.save(chemin_sortie)
        return chemin_sortie
    except Exception as e:
        print(f"[TTS] Échec de la synthèse vocale : {e}")
        return None


def jouer(chemin_fichier: str):
    """Joue un fichier audio (mp3) sur les haut-parleurs/casque."""
    try:
        playsound(chemin_fichier)
    except Exception as e:
        print(f"[TTS] Échec de la lecture audio : {e}")


def parler(texte: str):
    """
    Fonction tout-en-un à appeler depuis le pipeline : synthétise puis joue
    le texte à voix haute, en français. Échoue silencieusement (juste un
    message dans la console) si la synthèse ou la lecture échoue, pour ne
    pas bloquer le reste du pipeline pendant la démo.
    """
    chemin = synthetiser(texte)
    if chemin:
        jouer(chemin)
        try:
            os.remove(chemin)
        except OSError:
            pass  # pas grave si le nettoyage échoue, juste un fichier temp en plus


if __name__ == "__main__":
    parler(
        "Bonjour, je suis le compagnon d'écoute d'Ataraxia. "
        "Comment te sens-tu aujourd'hui ?"
    )