"""Backend web Ataraxia — FastAPI (endpoints async, TTS parallèle).

Endpoints :
  GET  /                                  → index HTML
  GET  /static/*                          → JS/CSS/assets
  GET  /api/themes                        → liste des thèmes
  POST /api/session/start                 → démarre une séance (opening + audio TTS)
  POST /api/session/{sid}/turn            → transcription + réponse psy (voix + sentiment)
  POST /api/session/{sid}/reformulate     → reformule la dernière question, sans avancer
  POST /api/session/{sid}/finish          → enrichit description + lance génération monde
  GET  /api/world/{world_id}/status       → poll état génération Marble

Lancer depuis workshop-b3-projet/ :
    uvicorn orchestrator.server:app --reload
"""

from __future__ import annotations

import asyncio
import base64
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai.conversation import PsySession
from ai.prompts import TOURS_PAR_SEANCE, VOICE_TRANSCRIPTION_PROMPT, list_themes
from marble.client import (
    MarbleAPIError,
    MarbleClient,
    MarbleOutOfCreditsError,
    WorldRef,
)
from voice import tts

# ---------------------------------------------------------------------------
# App + statique
# ---------------------------------------------------------------------------

app = FastAPI(title="Ataraxia")
WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

_sessions: dict[str, PsySession] = {}
_marble = MarbleClient()
_worlds: dict[str, WorldRef] = {}
_ready_audio_cache: dict[str, str] = {}


INVITE_CLOSE_TEXT = (
    "Ferme les yeux un instant. Prends une respiration lente. "
    "Ton monde se prépare doucement."
)
INVITE_OPEN_TEXT = (
    "Tu peux ouvrir les yeux. Ton monde t'attend. "
    "Es-tu prêt à y entrer ?"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _transcribe_bytes(data: bytes, filename: str = "audio.webm") -> str:
    """STT via Groq Whisper large-v3-turbo, accepte webm/mp3/wav directement."""
    from groq import Groq

    if not os.environ.get("GROQ_API_KEY"):
        raise HTTPException(500, "GROQ_API_KEY manquante côté serveur.")
    client = Groq()
    result = client.audio.transcriptions.create(
        file=(filename, data),
        model="whisper-large-v3-turbo",
        language="fr",
        prompt=VOICE_TRANSCRIPTION_PROMPT,
        response_format="text",
    )
    return str(result).strip()


async def _tts_b64(text: str) -> str | None:
    """Synthétise avec Edge TTS et renvoie l'audio en base64 (MP3), version async."""
    if not text:
        return None
    tmp = Path(tempfile.gettempdir()) / f"ataraxia_tts_{uuid.uuid4().hex}.mp3"
    try:
        await tts.synth_async(text, tmp)
        return base64.b64encode(tmp.read_bytes()).decode()
    except Exception as e:
        print(f"[tts] échec synth : {type(e).__name__}: {e}")
        return None
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/themes")
def themes() -> dict:
    return {"themes": list_themes(), "total_turns": TOURS_PAR_SEANCE}


class StartReq(BaseModel):
    theme: str


@app.post("/api/session/start")
async def start(req: StartReq) -> dict:
    if req.theme not in list_themes():
        raise HTTPException(400, f"Thème inconnu (dispo : {list_themes()})")
    session = PsySession(theme=req.theme)  # type: ignore[arg-type]
    sid = uuid.uuid4().hex
    _sessions[sid] = session
    opening = session.opening()
    return {
        "session_id": sid,
        "turn": 0,
        "total_turns": TOURS_PAR_SEANCE,
        "psy_text": opening,
        "psy_audio_b64": await _tts_b64(opening),
    }


@app.post("/api/session/{sid}/turn")
async def turn(sid: str, audio: UploadFile = File(...)) -> dict:
    session = _sessions.get(sid)
    if session is None:
        raise HTTPException(404, "Session inconnue.")

    data = await audio.read()
    if not data:
        raise HTTPException(400, "Audio vide.")

    filename = audio.filename or "audio.webm"
    transcript = _transcribe_bytes(data, filename)
    if not transcript:
        return {
            "turn": session.user_turns(),
            "user_text": "",
            "psy_text": None,
            "psy_audio_b64": None,
            "sentiment": {"emotion_principale": "neutre"},
            "is_finished": session.is_finished(),
            "empty": True,
        }

    response, sentiment = session.user_says(transcript)
    return {
        "turn": session.user_turns(),
        "user_text": transcript,
        "psy_text": response,
        "psy_audio_b64": await _tts_b64(response) if response else None,
        "sentiment": sentiment,
        "is_finished": session.is_finished(),
    }


@app.post("/api/session/{sid}/reformulate")
async def reformulate(sid: str) -> dict:
    """Reformule la dernière question du psy sans faire avancer le tour."""
    session = _sessions.get(sid)
    if session is None:
        raise HTTPException(404, "Session inconnue.")

    new_text = session.reformulate_last()
    if not new_text:
        raise HTTPException(400, "Rien à reformuler pour le moment.")
    return {
        "psy_text": new_text,
        "psy_audio_b64": await _tts_b64(new_text),
    }


@app.post("/api/session/{sid}/finish")
async def finish(sid: str) -> dict:
    """Enrichit la description et lance la génération Marble. Ne bloque PAS."""
    session = _sessions.get(sid)
    if session is None:
        raise HTTPException(404, "Session inconnue.")
    if not session.is_finished():
        raise HTTPException(400, "Séance non encore terminée.")

    enriched = session.enrich_world_description(session.last_user_text())
    try:
        world = _marble.generate_world(
            enriched["description"],
            details=enriched["details"],
        )
    except MarbleOutOfCreditsError as e:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "marble_out_of_credits",
                "message": (
                    "Le compte World Labs n'a plus de crédits pour générer un "
                    "nouveau monde. Recharge sur "
                    "https://platform.worldlabs.ai/billing puis réessaie."
                ),
                "upstream": e.detail,
            },
        )
    except MarbleAPIError as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "marble_api_error",
                "message": f"Marble a refusé la génération ({e.status_code}).",
                "upstream": e.detail,
            },
        )
    _worlds[world.world_id] = world

    # Génère les 2 TTS (description + invitation à fermer les yeux) en parallèle.
    desc_audio, close_audio = await asyncio.gather(
        _tts_b64(enriched["description"]),
        _tts_b64(INVITE_CLOSE_TEXT),
    )

    return {
        "world_id": world.world_id,
        "operation_id": world.operation_id,
        "status": world.status,
        "done": world.done,
        "description": enriched["description"],
        "details": enriched["details"],
        "viewer_url": world.viewer_url,
        "stub_mode": _marble.stub_mode,
        "audio": {
            "description_b64": desc_audio,
            "close_b64": close_audio,
        },
        "invite_close_text": INVITE_CLOSE_TEXT,
    }


@app.get("/api/world/{world_id}/status")
async def world_status(world_id: str) -> dict:
    world = _worlds.get(world_id)
    if world is None:
        raise HTTPException(404, "Monde inconnu.")
    _marble.get_status(world)

    audio_bundle: dict = {}
    invite_open_text: str | None = None
    if world.status == "ready":
        if world.world_id not in _ready_audio_cache:
            audio = await _tts_b64(INVITE_OPEN_TEXT)
            if audio:
                _ready_audio_cache[world.world_id] = audio
        audio_bundle["open_b64"] = _ready_audio_cache.get(world.world_id)
        invite_open_text = INVITE_OPEN_TEXT

    return {
        "world_id": world.world_id,
        "operation_id": world.operation_id,
        "status": world.status,
        "done": world.done,
        "viewer_url": world.viewer_url,
        "thumbnail_url": world.thumbnail_url,
        "assets": world.assets,
        "error": world.error,
        "audio": audio_bundle,
        "invite_open_text": invite_open_text,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("orchestrator.server:app", host="127.0.0.1", port=8000, reload=True)
