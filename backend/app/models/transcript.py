"""Pydantic models for transcript events."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import time


class TranscriptType(str, Enum):
    PARTIAL = "partial"   # interim – may change
    FINAL = "final"       # stable, committed


class TranscriptEvent(BaseModel):
    """Sent from backend → client via WebSocket."""

    type: TranscriptType
    session_id: str
    sequence: int = 0

    # ASR output
    transcript_en: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Translation output
    translation_fr: str = ""

    # Timing
    asr_latency_ms: Optional[float] = None
    translation_latency_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    server_ts: float = Field(default_factory=time.time)


class ErrorEvent(BaseModel):
    """Sent when a non-fatal error occurs (client should display warning)."""

    event: str = "error"
    code: str
    message: str
    recoverable: bool = True
    server_ts: float = Field(default_factory=time.time)


class StatusEvent(BaseModel):
    """Lifecycle events: connected, reconnecting, etc."""

    event: str  # "connected" | "reconnecting" | "disconnected"
    session_id: str = ""
    message: str = ""
    server_ts: float = Field(default_factory=time.time)
