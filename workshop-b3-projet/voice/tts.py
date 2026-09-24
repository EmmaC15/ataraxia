# Transforme un texte en audio (voix de synthèse Piper) et le joue
# directement sur les haut-parleurs/casque de l'utilisateur.
import subprocess
import sounddevice as sd
import soundfile as sf

VOICE_MODEL = "fr_FR-siwis-medium"

def parler(texte: str) -> None:
    fichier_sortie = "reponse_tts.wav"

    subprocess.run(
        ["piper", "--model", VOICE_MODEL, "--output_file", fichier_sortie],
        input=texte.encode("utf-8"),
        check=True,
    )

    data, samplerate = sf.read(fichier_sortie)
    sd.play(data, samplerate)
    sd.wait()