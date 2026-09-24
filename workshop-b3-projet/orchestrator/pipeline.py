"""Pipeline complet Ataraxia — CLI console.

Enchaîne : PsySession (Groq) → I/O audio → Marble (stub).

Lancer depuis workshop-b3-projet/ :
    python -m orchestrator.pipeline               # thème anxiete, TTS ON
    python -m orchestrator.pipeline stress
    python -m orchestrator.pipeline anxiete --mute   # texte seul, sans TTS
"""

from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path

from ai.conversation import PsySession
from ai.prompts import Theme, list_themes
from marble.client import MarbleClient
from voice import audio_device, transcribe, tts


def _say(text: str, speak: bool) -> None:
    print(f"\n🌿 Psy : {text}")
    if speak:
        try:
            tts.speak(text)
        except Exception as e:
            print(f"[tts désactivé : {e}]")


def _listen() -> str:
    input("(ENTRÉE pour parler, ENTRÉE encore pour arrêter) ")
    audio = audio_device.record_until_enter()
    if audio.size == 0:
        return ""
    wav = Path(tempfile.gettempdir()) / f"ataraxia_user_{int(time.time())}.wav"
    audio_device.save_wav(wav, audio)
    text = transcribe.transcribe(wav)
    print(f"👤 Vous : {text}")
    return text


def run_session(theme: Theme = "anxiete", speak: bool = True) -> dict:
    session = PsySession(theme=theme)
    marble = MarbleClient()

    print(f"\n=== Séance Ataraxia — thème : {theme} ===")
    _say(session.opening(), speak)

    while not session.is_finished():
        user_text = _listen()
        if not user_text:
            print("(rien capté, on repose la question)")
            continue
        response, sentiment = session.user_says(user_text)
        emo = sentiment.get("emotion_principale", "?")
        print(f"   [sentiment détecté : {emo}]")
        if sentiment.get("alerte_detresse"):
            print("   ⚠️  Alerte détresse détectée — orienter vers le 3114.")
        if response is not None:
            _say(response, speak)

    print("\n--- Séance close. Génération du monde apaisant… ---")
    enriched = session.enrich_world_description(session.last_user_text())
    print(f"\n🌍 Description : {enriched['description']}\n")
    if enriched["details"]:
        print("   Détails :")
        for k, v in enriched["details"].items():
            print(f"     - {k} : {v}")

    world = marble.generate_world(
        enriched["description"],
        details=enriched["details"],
    )
    print(f"\n✨ Génération lancée : id={world.world_id}  statut={world.status}")
    if not marble.stub_mode and world.status != "ready":
        print("   Attente de la fin de génération (~5 min)…")
        try:
            marble.wait_for_ready(world)
        except Exception as e:
            print(f"   ⚠ génération non terminée : {e}")
    if world.viewer_url:
        print(f"   🌍 Explorer : {world.viewer_url}")

    return {
        "theme": theme,
        "history": [(t.role, t.content) for t in session.history],
        "world_description": enriched["description"],
        "world_details": enriched["details"],
        "world_id": world.world_id,
        "viewer_url": world.viewer_url,
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline Ataraxia — CLI.")
    p.add_argument(
        "theme",
        nargs="?",
        default="anxiete",
        choices=list_themes(),
        help="Thème de la séance (défaut : anxiete).",
    )
    p.add_argument(
        "--mute",
        action="store_true",
        help="Désactive le TTS (texte seul).",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_session(theme=args.theme, speak=not args.mute)
