"""STT Ataraxia — Groq Whisper large-v3-turbo, biaisé par VOICE_TRANSCRIPTION_PROMPT."""

from __future__ import annotations

import os
from pathlib import Path

from ai.prompts import VOICE_TRANSCRIPTION_PROMPT

DEFAULT_MODEL = "whisper-large-v3-turbo"
DEFAULT_LANGUAGE = "fr"


def transcribe(
    wav_path: Path | str,
    model: str = DEFAULT_MODEL,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Transcrit un fichier audio via Groq. Retourne la chaîne nettoyée."""
    from groq import Groq

    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY manquante. Ajoute-la dans workshop-b3-projet/.env."
        )

    wav_path = Path(wav_path)
    client = Groq()
    with wav_path.open("rb") as f:
        result = client.audio.transcriptions.create(
            file=(wav_path.name, f.read()),
            model=model,
            language=language,
            prompt=VOICE_TRANSCRIPTION_PROMPT,
            response_format="text",
        )
    return str(result).strip()
