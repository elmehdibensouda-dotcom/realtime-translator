"""Abstract base class for all ASR providers."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.models.transcript import TranscriptEvent


class BaseASRService(ABC):
    """
    Each ASR implementation must implement `transcribe_stream`.

    The generator yields TranscriptEvent objects as audio bytes arrive.
    Implementation must:
    - Accept raw PCM 16-bit little-endian mono audio bytes
    - Yield PARTIAL events for interim results
    - Yield FINAL events when an utterance boundary is detected
    - Handle its own internal reconnection logic
    """

    @abstractmethod
    async def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes, None],
        session_id: str,
    ) -> AsyncGenerator[TranscriptEvent, None]:
        """Consume audio chunks, yield transcript events."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release resources (connections, etc.)."""
        ...
