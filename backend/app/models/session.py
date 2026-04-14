"""Session lifecycle model."""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SessionState(str, Enum):
    CONNECTING = "connecting"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class TranslatorSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    state: SessionState = SessionState.CONNECTING
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    sequence: int = 0
    bytes_received: int = 0
    frames_processed: int = 0
    errors: int = 0

    def touch(self) -> None:
        self.last_activity = time.time()

    def next_seq(self) -> int:
        self.sequence += 1
        return self.sequence

    @property
    def age_s(self) -> float:
        return time.time() - self.created_at

    @property
    def idle_s(self) -> float:
        return time.time() - self.last_activity
