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

    # ── ASR ──────────────────────────────────────────────────────────────────
    # Choices: "deepgram" | "google" | "whisper" | "assemblyai"
    ASR_PROVIDER: str = "assemblyai"
    DEEPGRAM_API_KEY: str = ""
    ASSEMBLYAI_API_KEY: str = "b47f2d35fcaf42029743204346b1584e"
    GOOGLE_SPEECH_CREDENTIALS_JSON: str = ""   # path or inline JSON
    OPENAI_API_KEY: str = ""                   # for Whisper fallback

    # ── Translation ──────────────────────────────────────────────────────────
    # Choices: "deepl" | "google" | "llm"
    TRANSLATION_PROVIDER: str = "deepl"
    DEEPL_API_KEY: str = ""
    GOOGLE_TRANSLATE_API_KEY: str = ""

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
