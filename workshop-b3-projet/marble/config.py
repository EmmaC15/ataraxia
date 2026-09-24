"""Configuration marble.worldlabs — lue depuis les variables d'environnement / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


DEFAULT_BASE_URL = "https://api.worldlabs.ai"
DEFAULT_MODEL = "marble-1.0-draft"          # standard ; "marble-1.1-plus" pour grands espaces
DEFAULT_POLL_INTERVAL_S = 12
DEFAULT_TIMEOUT_S = 480               # ~8 min, la génération prend ~5 min


@dataclass
class MarbleConfig:
    api_key: str | None
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    poll_interval_s: int = DEFAULT_POLL_INTERVAL_S
    timeout_s: int = DEFAULT_TIMEOUT_S


def load() -> MarbleConfig:
    return MarbleConfig(
        api_key=os.environ.get("MARBLE_API_KEY"),
        base_url=os.environ.get("MARBLE_BASE_URL", DEFAULT_BASE_URL),
        model=os.environ.get("MARBLE_MODEL", DEFAULT_MODEL),
        poll_interval_s=int(os.environ.get("MARBLE_POLL_INTERVAL_S", DEFAULT_POLL_INTERVAL_S)),
        timeout_s=int(os.environ.get("MARBLE_TIMEOUT_S", DEFAULT_TIMEOUT_S)),
    )
