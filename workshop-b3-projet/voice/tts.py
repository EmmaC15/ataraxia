"""TTS Ataraxia — Microsoft Edge TTS (voix française chaleureuse, gratuit).

- `synth(text, out_path)` : synthétise dans un fichier MP3, renvoie le chemin.
- `speak(text)` : synthétise + joue immédiatement (bloquant).
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import time
from pathlib import Path

DEFAULT_VOICE = "fr-FR-DeniseNeural"  # féminine, chaleureuse, très fluide


async def synth_async(text: str, out_path: Path | str, voice: str = DEFAULT_VOICE) -> Path:
    """Version asynchrone (à utiliser depuis un serveur async type FastAPI)."""
    import edge_tts

    out_path = Path(out_path)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))
    return out_path


def synth(text: str, out_path: Path | str, voice: str = DEFAULT_VOICE) -> Path:
    """Version bloquante (pour scripts CLI). N'utiliser QUE hors event-loop.

    Un `asyncio.run()` échoue si un loop est déjà actif (contexte FastAPI).
    Depuis FastAPI ou tout code async, appeler `synth_async` directement.
    """
    out_path = Path(out_path)
    return asyncio.run(synth_async(text, out_path, voice))


def speak(text: str, voice: str = DEFAULT_VOICE) -> None:
    """Synthétise puis joue immédiatement le texte via pygame.mixer (bloquant)."""
    if not text.strip():
        return

    tmp = Path(tempfile.gettempdir()) / f"ataraxia_tts_{os.getpid()}_{int(time.time()*1000)}.mp3"
    synth(text, tmp, voice)

    # pygame.mixer lit nativement le MP3, cross-platform, sans ffmpeg.
    import pygame

    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(str(tmp))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    pygame.mixer.music.unload()

    try:
        tmp.unlink()
    except OSError:
        pass
