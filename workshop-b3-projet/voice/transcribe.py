"""
Brique voix : enregistre le micro avec détection automatique de fin de
parole (silence), transcrit avec faster-whisper en utilisant le prompt
d'orientation d'Ataraxia pour une meilleure précision sur le vocabulaire
émotionnel.

Fonction principale à utiliser dans le pipeline : ecouter_et_transcrire()
"""

import sys
import time
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from ai.prompts import VOICE_TRANSCRIPTION_PROMPT
from voice.audio_device import obtenir_index_micro

SAMPLE_RATE = 16000  # taux attendu par Whisper
TAILLE_BLOC = 480  # ~30ms par bloc à 16kHz, bon compromis réactivité/précision

# Réglages de détection de silence — à ajuster si ça coupe trop tôt/tard
SEUIL_VOLUME = 0.015          # volume RMS au-dessus duquel on considère "on parle"
DUREE_SILENCE_FIN = 1.2       # secondes de silence après la parole pour arrêter
DUREE_MAX_ENREGISTREMENT = 30.0  # garde-fou : arrêt forcé même si ça ne s'arrête jamais
DUREE_MAX_ATTENTE_PAROLE = 8.0   # garde-fou : si personne ne parle du tout

# "small" est un bon compromis vitesse/qualité en français sur CPU.
# Passez à "base" si c'est trop lent sur votre machine, ou "medium" si vous
# avez un GPU et voulez plus de précision.
TAILLE_MODELE = "small"

_modele = None  # chargé une seule fois (lazy loading)


def _charger_modele() -> WhisperModel:
    global _modele
    if _modele is None:
        print("Chargement du modèle Whisper (une seule fois)...")
        _modele = WhisperModel(TAILLE_MODELE, device="cpu", compute_type="int8")
    return _modele


def _rms(bloc: np.ndarray) -> float:
    """Calcule le volume (RMS) d'un bloc audio."""
    return float(np.sqrt(np.mean(np.square(bloc))))


def enregistrer_avec_detection_silence(forcer_pc: bool = False) -> np.ndarray:
    """
    Enregistre le micro jusqu'à détecter la fin de la parole (silence
    prolongé après que la personne a commencé à parler).
    Renvoie les données audio en tableau numpy (float32, mono, 16kHz).
    """
    index_micro = obtenir_index_micro(forcer_pc=forcer_pc)

    print("🎙️  En écoute... parlez quand vous êtes prêt.")

    blocs_captes = []
    a_commence_a_parler = False
    debut = time.time()
    dernier_instant_parole = None

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=index_micro,
        blocksize=TAILLE_BLOC,
    ) as stream:
        while True:
            bloc, _ = stream.read(TAILLE_BLOC)
            bloc = bloc.flatten()
            volume = _rms(bloc)
            maintenant = time.time()

            if volume > SEUIL_VOLUME:
                if not a_commence_a_parler:
                    print("🗣️  Parole détectée...")
                a_commence_a_parler = True
                dernier_instant_parole = maintenant
                blocs_captes.append(bloc)
            elif a_commence_a_parler:
                # on a déjà commencé à parler, on garde le silence dans le
                # buffer (naturel dans la phrase) mais on surveille la durée
                blocs_captes.append(bloc)
                if maintenant - dernier_instant_parole > DUREE_SILENCE_FIN:
                    print("🤫 Fin de parole détectée.")
                    break

            # Garde-fous
            if not a_commence_a_parler and (maintenant - debut) > DUREE_MAX_ATTENTE_PAROLE:
                print("⏱️  Personne n'a parlé, arrêt de l'écoute.")
                break
            if (maintenant - debut) > DUREE_MAX_ENREGISTREMENT:
                print("⏱️  Durée maximale atteinte, arrêt forcé.")
                break

    if not blocs_captes:
        return np.array([], dtype="float32")

    return np.concatenate(blocs_captes)


def transcrire(audio: np.ndarray) -> str:
    """Transcrit un tableau audio numpy en texte, en français."""
    if audio.size == 0:
        return ""

    modele = _charger_modele()
    segments, _ = modele.transcribe(
        audio,
        language="fr",
        initial_prompt=VOICE_TRANSCRIPTION_PROMPT,
    )
    texte = " ".join(segment.text.strip() for segment in segments)
    return texte.strip()


def _vider_buffer_clavier():
    """
    Vide les touches déjà pressées et en attente (ex: Entrée pressée pendant
    que le psy parlait) pour éviter qu'elles ne déclenchent immédiatement
    l'arrêt de l'enregistrement suivant sans laisser le temps de répondre.
    """
    try:
        import msvcrt  # Windows
        while msvcrt.kbhit():
            msvcrt.getch()
    except ImportError:
        try:
            import termios  # Linux/Mac
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except Exception:
            pass


def enregistrer_jusqua_entree(forcer_pc: bool = False) -> np.ndarray:
    """
    Enregistre le micro jusqu'à ce que l'utilisateur appuie sur Entrée.
    Plus simple et plus fiable qu'une détection automatique pour une démo
    live — pas de risque de coupure trop tôt/trop tard.
    Renvoie les données audio en tableau numpy (float32, mono, 16kHz).
    """
    index_micro = obtenir_index_micro(forcer_pc=forcer_pc)
    blocs_captes = []

    def callback(indata, frames, temps, statut):
        blocs_captes.append(indata.copy().flatten())

    _vider_buffer_clavier()
    print("🎙️  Parlez, puis appuyez sur Entrée quand vous avez fini...")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=index_micro,
        blocksize=TAILLE_BLOC,
        callback=callback,
    ):
        input()  # bloque jusqu'à la touche Entrée, l'enregistrement continue en arrière-plan

    print("✅ Enregistrement terminé.")

    if not blocs_captes:
        return np.array([], dtype="float32")

    return np.concatenate(blocs_captes)


def ecouter_et_transcrire(forcer_pc: bool = False, mode: str = "entree") -> str:
    """
    Fonction tout-en-un à appeler depuis le pipeline.
    mode="entree" (par défaut) : enregistre jusqu'à la touche Entrée (fiable
    pour une démo live, recommandé).
    mode="silence" : détection automatique de fin de parole (mains libres,
    mais peut couper trop tôt/tard selon le réglage du seuil).

    Si rien n'est capté (silence total, micro pas branché...), retente une
    fois avant d'abandonner, pour éviter de faire planter la séance sur un
    simple raté de micro.
    """
    for tentative in range(2):
        if mode == "silence":
            audio = enregistrer_avec_detection_silence(forcer_pc=forcer_pc)
        else:
            audio = enregistrer_jusqua_entree(forcer_pc=forcer_pc)

        texte = transcrire(audio)
        if texte:
            return texte

        if tentative == 0:
            print("🔇 Je n'ai rien entendu, on réessaie...")

    print("🔇 Toujours rien entendu, on continue quand même.")
    return ""


if __name__ == "__main__":
    texte = ecouter_et_transcrire(mode="entree")
    print("\nTexte transcrit :")
    print(texte)