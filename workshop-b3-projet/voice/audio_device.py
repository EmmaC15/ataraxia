"""Enregistrement et lecture audio pour Ataraxia.

Module réutilisable par le CLI (`scripts/record_and_transcribe.py`)
et par l'orchestrateur (`orchestrator/pipeline.py`).
"""

from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLERATE = 16_000  # cible native de Whisper
CHANNELS = 1


def record_until_stop(stop_event: threading.Event) -> np.ndarray:
    """Enregistre depuis le micro par défaut jusqu'à ce que `stop_event` soit set."""
    q: queue.Queue[np.ndarray] = queue.Queue()

    def _cb(indata, _frames, _time, status):
        if status:
            print(f"[audio] {status}", file=sys.stderr)
        q.put(indata.copy())

    chunks: list[np.ndarray] = []
    with sd.InputStream(
        samplerate=SAMPLERATE,
        channels=CHANNELS,
        dtype="int16",
        callback=_cb,
    ):
        while not stop_event.is_set():
            try:
                chunks.append(q.get(timeout=0.1))
            except queue.Empty:
                continue

    if not chunks:
        return np.zeros((0, CHANNELS), dtype="int16")
    return np.concatenate(chunks, axis=0)


def record_until_enter() -> np.ndarray:
    """Variante interactive : s'arrête quand l'utilisateur appuie sur ENTRÉE."""
    stop = threading.Event()

    def _wait():
        try:
            input()
        except EOFError:
            pass
        stop.set()

    threading.Thread(target=_wait, daemon=True).start()
    return record_until_stop(stop)


def play(audio: np.ndarray, samplerate: int = SAMPLERATE) -> None:
    """Rejoue un tableau numpy audio (bloquant jusqu'à la fin)."""
    if audio.size == 0:
        return
    sd.play(audio, samplerate)
    sd.wait()


def play_wav(path: Path) -> None:
    """Rejoue un fichier WAV depuis le disque."""
    data, sr = sf.read(str(path), dtype="int16")
    play(data, sr)


def save_wav(path: Path, audio: np.ndarray, samplerate: int = SAMPLERATE) -> Path:
    """Écrit `audio` en WAV 16-bit à `path`, renvoie le chemin."""
    sf.write(str(path), audio, samplerate)
    return path
