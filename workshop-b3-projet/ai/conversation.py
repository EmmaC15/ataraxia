"""Boucle de dialogue psy Ataraxia — appels Groq (LLM texte→texte).

Le LLM génère toutes les questions dynamiquement à partir de la conversation.
Le tour numéro est injecté dans chaque message user pour que le modèle sache
quand clôturer par "décris-moi ton lieu apaisant".

Deux modèles :
- `DEFAULT_CHAT_MODEL` : gros modèle pour le psy + l'enrichissement description.
- `DEFAULT_FAST_MODEL` : petit modèle rapide pour l'analyse de sentiment.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Literal

from ai.prompts import (
    TOURS_PAR_SEANCE,
    Theme,
    build_psy_system_prompt,
    build_sentiment_messages,
    build_world_description_messages,
    opening_question,
    parse_world_description,
)

DEFAULT_CHAT_MODEL = "openai/gpt-oss-120b"   # psy + enrichissement description
DEFAULT_FAST_MODEL = "openai/gpt-oss-20b"    # analyse de sentiment (JSON)


@dataclass
class Turn:
    role: Literal["user", "assistant"]
    content: str
    sentiment: dict | None = None


@dataclass
class PsySession:
    """Une séance = ~10 tours de dialogue.

    Ordre typique :
        s = PsySession(theme="anxiete")
        print(s.opening())                       # -> question d'ouverture
        while not s.is_finished():
            user_text = ...                      # via STT
            reponse, sentiment = s.user_says(user_text)
            if reponse: print(reponse)           # reformulation + question adaptée
        world = s.enrich_world_description(s.last_user_text())
        # world = {"description": "...", "details": {...}}
    """

    theme: Theme
    model: str = DEFAULT_CHAT_MODEL
    sentiment_model: str = DEFAULT_FAST_MODEL
    history: list[Turn] = field(default_factory=list)
    _client: object = field(init=False, default=None, repr=False)

    def __post_init__(self):
        if not os.environ.get("GROQ_API_KEY"):
            raise RuntimeError(
                "GROQ_API_KEY manquante. Ajoute-la dans workshop-b3-projet/.env."
            )
        from groq import Groq
        self._client = Groq()

    # ------------------------------------------------------------------
    # État de la séance
    # ------------------------------------------------------------------

    def user_turns(self) -> int:
        return sum(1 for t in self.history if t.role == "user")

    def is_finished(self) -> bool:
        return self.user_turns() >= TOURS_PAR_SEANCE

    def last_user_text(self) -> str:
        for t in reversed(self.history):
            if t.role == "user":
                return t.content
        return ""

    # ------------------------------------------------------------------
    # Contexte LLM
    # ------------------------------------------------------------------

    def _messages(self) -> list[dict]:
        msgs: list[dict] = [
            {"role": "system", "content": build_psy_system_prompt(self.theme)}
        ]
        for t in self.history:
            msgs.append({"role": t.role, "content": t.content})
        return msgs

    def _annotated_user(self, text: str) -> str:
        """Injecte le tag [Tour X/N] pour que le LLM sache où on en est."""
        tour = self.user_turns() + 1  # ce tour-ci
        return f"[Tour {tour}/{TOURS_PAR_SEANCE}] {text.strip()}"

    # ------------------------------------------------------------------
    # Interactions
    # ------------------------------------------------------------------

    def opening(self) -> str:
        """Ouvre la séance avec la question d'ouverture du thème."""
        q = opening_question(self.theme)
        self.history.append(Turn("assistant", q))
        return q

    def user_says(
        self,
        text: str,
        voice_features: dict[str, str] | None = None,
    ) -> tuple[str | None, dict]:
        """Enregistre la réponse user, analyse le sentiment, génère la réplique psy.

        Retourne (reponse_psy, sentiment).
        `reponse_psy` est None si on est déjà à la fin de la séance.
        """
        sentiment = self._analyze_sentiment(text, voice_features or {})
        annotated = self._annotated_user(text)
        self.history.append(Turn("user", annotated, sentiment=sentiment))

        if self.is_finished():
            return None, sentiment

        response = self._chat(self._messages(), temperature=0.7)
        self.history.append(Turn("assistant", response))
        return response, sentiment

    def reformulate_last(self) -> str | None:
        """Reformule la dernière question du psy avec d'autres mots.

        N'avance PAS le compteur de tours et ne modifie pas les réponses user.
        Remplace la dernière réplique `assistant` dans l'historique.
        """
        last_idx = None
        for i in range(len(self.history) - 1, -1, -1):
            if self.history[i].role == "assistant":
                last_idx = i
                break
        if last_idx is None:
            return None

        msgs: list[dict] = [
            {"role": "system", "content": build_psy_system_prompt(self.theme)}
        ]
        for t in self.history[: last_idx + 1]:
            msgs.append({"role": t.role, "content": t.content})
        msgs.append({
            "role": "user",
            "content": (
                "[Peux-tu reformuler ta dernière question autrement, avec "
                "d'autres mots ? Sans changer de sujet, sans en poser une "
                "nouvelle, et sans dire que tu reformules.]"
            ),
        })
        new_text = self._chat(msgs, temperature=0.7)
        self.history[last_idx] = Turn("assistant", new_text)
        return new_text

    def enrich_world_description(self, user_input: str) -> dict:
        """Transforme la description brute en {description, details} pour marble.

        Tolérant : si le LLM refuse (safety) ou renvoie un JSON invalide, on
        retombe sur la description brute de l'utilisateur. Marble accepte des
        prompts textes simples, donc le flow continue au lieu de crasher en 500.
        """
        text = (user_input or "").strip()
        if not text:
            return {"description": "", "details": {}}
        try:
            msgs = build_world_description_messages(text)
            raw = self._chat(msgs, temperature=0.8, json_mode=True)
            parsed = parse_world_description(raw)
            if not parsed.get("description"):
                return {"description": text, "details": {}}
            return parsed
        except Exception as e:
            # Cas typiques : groq.BadRequestError json_validate_failed
            # (le modèle a refusé et renvoyé du texte), timeout, quota.
            print(f"[enrich] fallback description brute — {type(e).__name__}: {e}")
            return {"description": text, "details": {}}

    # ------------------------------------------------------------------
    # Appels Groq
    # ------------------------------------------------------------------

    def _chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> str:
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        r = self._client.chat.completions.create(**kwargs)  # type: ignore[attr-defined]
        return r.choices[0].message.content.strip()

    def _analyze_sentiment(self, text: str, voice_features: dict[str, str]) -> dict:
        msgs = build_sentiment_messages(text, voice_features)
        try:
            r = self._client.chat.completions.create(  # type: ignore[attr-defined]
                model=self.sentiment_model,
                messages=msgs,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            return json.loads(r.choices[0].message.content)
        except Exception as e:
            return {"emotion_principale": "neutre", "erreur": str(e)}
