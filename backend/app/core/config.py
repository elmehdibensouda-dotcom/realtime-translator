"""Centralised configuration – loaded from environment / .env file."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="config.env", env_file_encoding="utf-8", case_sensitive=False
    )

    # ── App ──────────────────────────────────────────────────────────────────
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]

    # ── Services (Free Mode) ─────────────────────────────────────────────────
    # The browser handles ASR (Web Speech API).
    # Translation uses Google via deep-translator.
    FREE_TRANSLATION_MAX_WORKERS: int = 10

    # ── WebSocket ────────────────────────────────────────────────────────────
    WS_PING_INTERVAL: int = 20        # seconds
    WS_PING_TIMEOUT: int = 10
    WS_MAX_MESSAGE_SIZE: int = 65536  # 64 KB per audio frame
    AUDIO_CHUNK_MS: int = 100         # target chunk duration

    # ── Session ──────────────────────────────────────────────────────────────
    MAX_CONCURRENT_SESSIONS: int = 500
    SESSION_TIMEOUT_S: int = 3600     # 1 hour

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60


settings = Settings()
