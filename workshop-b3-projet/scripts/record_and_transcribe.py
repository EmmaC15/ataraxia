"""CLI Ataraxia : enregistre la voix, (optionnel) rejoue, puis transcrit.

Usage :
    python scripts/record_and_transcribe.py
    python scripts/record_and_transcribe.py --model medium --output ma_prise.wav

Contrôle :
    - ENTRÉE pour démarrer l'enregistrement.
    - ENTRÉE à nouveau pour l'arrêter.
    - Puis choix "rejouer" et transcription automatique.

Dépendances (à installer une fois) :
    pip install sounddevice soundfile numpy groq python-dotenv

Requis dans workshop-b3-projet/.env :
    GROQ_API_KEY=gsk_...
"""

from __future__ import annotations

import argparse
import os
import queue
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

# Import du prompt d'orientation STT défini dans ai/prompts.py.
# On ajoute le parent au sys.path pour que le script soit exécutable directement.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ai.prompts import VOICE_TRANSCRIPTION_PROMPT  # noqa: E402

# Charge .env s'il existe, sans échouer si python-dotenv n'est pas installé.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


SAMPLERATE = 16_000  # 16 kHz mono — cible native de Whisper
CHANNELS = 1


def record_until_enter() -> np.ndarray:
    """Enregistre depuis le micro par défaut jusqu'à ce que l'utilisateur tape ENTRÉE."""
    audio_q: queue.Queue[np.ndarray] = queue.Queue()
    stop_event = threading.Event()

    def _callback(indata, frames, _time, status):
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        audio_q.put(indata.copy())

    def _wait_for_enter():
        try:
            input()
        except EOFError:
            pass
        stop_event.set()

    threading.Thread(target=_wait_for_enter, daemon=True).start()

    chunks: list[np.ndarray] = []
    with sd.InputStream(
        samplerate=SAMPLERATE,
        channels=CHANNELS,
        dtype="int16",
        callback=_callback,
    ):
        print("Enregistrement... (ENTRÉE pour arrêter)")
        while not stop_event.is_set():
            try:
                chunks.append(audio_q.get(timeout=0.1))
            except queue.Empty:
                continue

    if not chunks:
        return np.zeros((0, CHANNELS), dtype="int16")
    return np.concatenate(chunks, axis=0)


def play(audio: np.ndarray) -> None:
    """Rejoue l'audio sur la sortie par défaut."""
    if audio.size == 0:
        print("Rien à rejouer.")
        return
    sd.play(audio, SAMPLERATE)
    sd.wait()


def transcribe(wav_path: Path, model: str) -> str:
    """Transcrit un WAV via l'API Groq, en français, avec l'initial_prompt Ataraxia."""
    # Import différé : n'exige `groq` que si on atteint réellement la transcription.
    from groq import Groq

    if not os.environ.get("GROQ_API_KEY"):
        raise SystemExit(
            "GROQ_API_KEY manquante. Ajoute-la dans workshop-b3-projet/.env "
            "(ou exporte-la dans ton shell)."
        )

    print(f"Appel Groq ({model})...")
    client = Groq()
    with open(wav_path, "rb") as f:
        result = client.audio.transcriptions.create(
            file=(wav_path.name, f.read()),
            model=model,
            language="fr",
            prompt=VOICE_TRANSCRIPTION_PROMPT,
            response_format="text",
        )
    # response_format="text" renvoie directement une chaîne.
    return str(result).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enregistre, rejoue, transcrit — CLI Ataraxia.")
    parser.add_argument(
        "--model",
        default="whisper-large-v3-turbo",
        choices=["whisper-large-v3-turbo", "whisper-large-v3"],
        help=(
            "Modèle Whisper hébergé chez Groq. "
            "'whisper-large-v3-turbo' (défaut) = le plus rapide. "
            "'whisper-large-v3' = un poil plus précis, un peu plus lent."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Chemin du WAV de sortie (défaut : fichier temporaire horodaté).",
    )
    parser.add_argument(
        "--no-replay",
        action="store_true",
        help="Ne pas proposer de rejouer l'enregistrement.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_path = args.output or (
        Path(tempfile.gettempdir()) / f"ataraxia_{int(time.time())}.wav"
    )

    print("Appuie sur ENTRÉE pour démarrer l'enregistrement.")
    input()

    audio = record_until_enter()
    duree_s = len(audio) / SAMPLERATE
    if duree_s < 0.2:
        print("Enregistrement trop court, abandon.")
        return 1

    sf.write(output_path, audio, SAMPLERATE)
    print(f"Enregistré : {output_path} ({duree_s:.1f} s)")

    if not args.no_replay:
        reponse = input("Rejouer ? [o/N] ").strip().lower()
        if reponse == "o":
            play(audio)

    texte = transcribe(output_path, args.model)

    print("\n--- Transcription ---")
    print(texte if texte else "(aucun texte détecté)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
