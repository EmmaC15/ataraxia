"""Client marble.worldlabs — appelle la vraie API World Labs (docs.worldlabs.ai/api).

Endpoints utilisés :
- POST /marble/v1/worlds:generate                → lance la génération (async, ~5 min)
- GET  /marble/v1/operations/{operation_id}      → poll le statut
- GET  /marble/v1/worlds/{world_id}              → récupère assets + viewer_url

Auth : header `WLT-Api-Key: <clé>` (pas de "Bearer").

Fallback STUB : si `MARBLE_API_KEY` est absente, le client tourne en mode simulé
(log dans data/marble_stub_log.jsonl, WorldRef fictive immédiatement "ready").
Ça permet de tester tout le pipeline sans clé Marble.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from marble.config import MarbleConfig
from marble.config import load as load_config


class MarbleError(RuntimeError):
    """Erreur retournée par l'API Marble (dans le champ `error` d'une opération)."""


class MarbleAPIError(RuntimeError):
    """Erreur HTTP renvoyée par l'API Marble (auth, crédits, quota, prompt refusé…).

    Attributes
    ----------
    status_code : code HTTP (401/402/403/429/…)
    detail      : message serveur si disponible
    """

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Marble API {status_code}: {detail}")


class MarbleOutOfCreditsError(MarbleAPIError):
    """Le compte World Labs n'a plus assez de crédits pour lancer la génération."""

    def __init__(self, detail: str = ""):
        super().__init__(402, detail or "Insufficient API credits")


@dataclass
class WorldRef:
    world_id: str
    operation_id: str | None = None
    status: str = "pending"          # pending | in_progress | ready | failed
    done: bool = False
    description: str = ""
    details: dict = field(default_factory=dict)
    viewer_url: str | None = None     # https://marble.worldlabs.ai/world/{id}
    thumbnail_url: str | None = None
    assets: dict = field(default_factory=dict)
    error: dict | None = None


class MarbleClient:
    def __init__(self, config: MarbleConfig | None = None):
        self.config = config or load_config()
        self.stub_mode = not self.config.api_key
        self.log_path = (
            Path(__file__).resolve().parent.parent / "data" / "marble_stub_log.jsonl"
        )
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def generate_world(
        self,
        description: str,
        details: dict | None = None,
        display_name: str | None = None,
        model: str | None = None,
    ) -> WorldRef:
        """Lance la génération d'un monde. Retourne un WorldRef non encore ready.

        Utiliser `wait_for_ready()` pour bloquer jusqu'à la fin (~5 min),
        ou `get_status()` pour poller manuellement (utile côté API web).
        """
        details = details or {}
        display_name = display_name or self._auto_display_name(description)

        if self.stub_mode:
            return self._stub_generate(description, details, display_name)

        payload = {
            "display_name": display_name,
            "model": model or self.config.model,
            "world_prompt": {
                "type": "text",
                "text_prompt": description,
                "is_pano": "auto",
            },
        }
        body = self._post("/marble/v1/worlds:generate", payload)
        ref = self._ref_from_operation(body, description, details)
        # Le POST /worlds:generate renvoie metadata: null au tout début — Marble
        # peuple world_id quelques instants après. Un premier poll le récupère.
        if ref.operation_id and not ref.world_id:
            try:
                self.get_status(ref)
            except Exception:
                pass
        return ref

    def get_status(self, ref: WorldRef) -> WorldRef:
        """Rafraîchit `ref` en polling l'opération. Ne bloque pas."""
        if self.stub_mode:
            ref.status = "ready"
            ref.done = True
            return ref
        if not ref.operation_id:
            return ref

        op = self._get(f"/marble/v1/operations/{ref.operation_id}")
        ref.done = bool(op.get("done"))
        metadata = op.get("metadata") or {}
        progress = metadata.get("progress") or {}
        # Récupère le world_id dès qu'il apparaît (peut être null au tout début).
        latest_world_id = metadata.get("world_id")
        if latest_world_id and latest_world_id != ref.world_id:
            ref.world_id = latest_world_id
            ref.viewer_url = f"https://marble.worldlabs.ai/world/{latest_world_id}"
        raw_status = (progress.get("status") or "").lower()
        # Normalisation : IN_PROGRESS -> in_progress, SUCCEEDED -> ready.
        if raw_status == "succeeded":
            ref.status = "ready"
        elif raw_status == "in_progress":
            ref.status = "in_progress"

        if op.get("error"):
            ref.status = "failed"
            ref.error = op["error"]
            return ref

        if ref.done and ref.status == "ready":
            self._hydrate_assets(ref)
        return ref

    def wait_for_ready(
        self,
        ref: WorldRef,
        poll_interval_s: int | None = None,
        timeout_s: int | None = None,
    ) -> WorldRef:
        """Bloque jusqu'à ce que le monde soit ready (ou timeout / failed)."""
        if self.stub_mode or ref.status == "ready":
            return ref
        interval = poll_interval_s or self.config.poll_interval_s
        deadline = time.time() + (timeout_s or self.config.timeout_s)
        while time.time() < deadline:
            self.get_status(ref)
            if ref.status == "ready":
                return ref
            if ref.status == "failed":
                raise MarbleError(ref.error or {"message": "génération échouée"})
            time.sleep(interval)
        raise TimeoutError(
            f"Marble n'a pas terminé après {timeout_s or self.config.timeout_s}s "
            f"(operation_id={ref.operation_id})."
        )

    # ------------------------------------------------------------------
    # Interne
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {
            "WLT-Api-Key": self.config.api_key or "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, path: str, payload: dict) -> dict:
        import httpx
        r = httpx.post(
            f"{self.config.base_url}{path}",
            headers=self._headers(),
            json=payload,
            timeout=30.0,
        )
        self._raise_for_status(r)
        return r.json()

    def _get(self, path: str) -> dict:
        import httpx
        r = httpx.get(
            f"{self.config.base_url}{path}",
            headers=self._headers(),
            timeout=30.0,
        )
        self._raise_for_status(r)
        return r.json()

    def _raise_for_status(self, r) -> None:
        if r.status_code < 400:
            return
        detail = ""
        try:
            body = r.json()
            detail = body.get("detail") or body.get("message") or str(body)
        except Exception:
            detail = (r.text or "")[:500]
        if r.status_code == 402:
            raise MarbleOutOfCreditsError(detail)
        raise MarbleAPIError(r.status_code, detail)

    def _ref_from_operation(
        self, op_body: dict, description: str, details: dict
    ) -> WorldRef:
        metadata = op_body.get("metadata") or {}
        progress = metadata.get("progress") or {}
        world_id = metadata.get("world_id", "")
        raw_status = (progress.get("status") or "").lower()
        status = "ready" if raw_status == "succeeded" else (raw_status or "pending")
        ref = WorldRef(
            world_id=world_id,
            operation_id=op_body.get("operation_id"),
            status=status,
            done=bool(op_body.get("done")),
            description=description,
            details=details,
            viewer_url=f"https://marble.worldlabs.ai/world/{world_id}" if world_id else None,
            error=op_body.get("error"),
        )
        return ref

    def _hydrate_assets(self, ref: WorldRef) -> None:
        try:
            body = self._get(f"/marble/v1/worlds/{ref.world_id}")
        except Exception:
            return
        world = body.get("world") or {}
        ref.assets = world.get("assets") or {}
        ref.viewer_url = world.get("world_marble_url") or ref.viewer_url
        imagery = ref.assets.get("imagery") or {}
        ref.thumbnail_url = imagery.get("pano_url") or (ref.assets.get("thumbnail_url") if isinstance(ref.assets.get("thumbnail_url"), str) else None)

    def _auto_display_name(self, description: str) -> str:
        # Marble impose max 64 chars sur display_name (contrainte serveur).
        prefix = "Ataraxia — "
        short = description.strip().replace("\n", " ")
        max_desc = 64 - len(prefix)
        if len(short) > max_desc:
            short = short[: max_desc - 1].rstrip() + "…"
        return prefix + short

    # ------------------------------------------------------------------
    # Mode stub (aucune clé)
    # ------------------------------------------------------------------

    def _stub_generate(
        self, description: str, details: dict, display_name: str
    ) -> WorldRef:
        ref = WorldRef(
            world_id=f"stub_{uuid.uuid4().hex[:12]}",
            operation_id=None,
            status="ready",
            done=True,
            description=description,
            details=details,
            viewer_url=None,
        )
        record = {
            "mode": "STUB (MARBLE_API_KEY manquante)",
            "display_name": display_name,
            "description": description,
            "details": details,
            "sent_at": time.time(),
            "world_id": ref.world_id,
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return ref
