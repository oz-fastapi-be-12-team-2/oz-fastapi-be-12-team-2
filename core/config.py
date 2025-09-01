from __future__ import annotations

import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

TORTOISE_ORM = {
    "connections": {"default": "postgres://diaryapi:diaryapi@db:5432/diaryapi"},
    "apps": {
        "models": {
            "models": [
                "app.diary.model",
                "app.user.model",
                "app.tag.model",
                "app.notification.model",
                "aerich.models",
            ],
            "default_connection": "default",
        },
    },
}


# ── helpers ───────────────────────────────────────────────────────
def _getenv_int(name: str, default: int) -> int:
    v = os.getenv(name)
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default


def _getenv_float(name: str, default: float) -> float:
    v = os.getenv(name)
    try:
        return float(v) if v is not None else default
    except ValueError:
        return default


# ── AI (typed + legacy 호환) ─────────────────────────────────────
@dataclass(frozen=True)
class AISettings:
    google_api_key: str | None
    model_name: str
    max_tokens: int
    temperature: float

    @property
    def enabled(self) -> bool:
        return bool(self.google_api_key)


def load_ai_settings() -> AISettings:
    return AISettings(
        google_api_key=os.getenv("GOOGLE_API_KEY") or None,
        model_name=os.getenv("AI_MODEL_NAME", "gemini-2.5-flash"),
        max_tokens=_getenv_int("AI_MAX_TOKENS", 1000),
        temperature=_getenv_float("AI_TEMPERATURE", 0.7),
    )


AI_SETTINGS_OBJ: AISettings = load_ai_settings()
AI_ENABLED: bool = AI_SETTINGS_OBJ.enabled

# 레거시 dict 접근 호환 (읽기 전용)
AI_SETTINGS: Mapping[str, object] = MappingProxyType(
    {
        "google_api_key": AI_SETTINGS_OBJ.google_api_key,
        "model_name": AI_SETTINGS_OBJ.model_name,
        "max_tokens": AI_SETTINGS_OBJ.max_tokens,
        "temperature": AI_SETTINGS_OBJ.temperature,
    }
)
