"""Lightweight in-process metrics (latency histograms, counters)."""

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class LatencyBucket:
    samples: Deque[float] = field(default_factory=lambda: deque(maxlen=1000))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, latency_ms: float) -> None:
        with self._lock:
            self.samples.append(latency_ms)

    def percentile(self, p: float) -> float:
        with self._lock:
            if not self.samples:
                return 0.0
            sorted_s = sorted(self.samples)
            idx = int(len(sorted_s) * p / 100)
            return sorted_s[min(idx, len(sorted_s) - 1)]

    def avg(self) -> float:
        with self._lock:
            return sum(self.samples) / len(self.samples) if self.samples else 0.0


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, LatencyBucket] = {}
        self._active_sessions: int = 0

    # ── Sessions ─────────────────────────────────────────────────────────────
    def session_opened(self) -> None:
        with self._lock:
            self._active_sessions += 1
            self._counters["sessions_total"] += 1

    def session_closed(self) -> None:
        with self._lock:
            self._active_sessions = max(0, self._active_sessions - 1)

    @property
    def active_sessions(self) -> int:
        return self._active_sessions

    # ── Latency ──────────────────────────────────────────────────────────────
    def record_latency(self, name: str, latency_ms: float) -> None:
        if name not in self._latencies:
            with self._lock:
                self._latencies.setdefault(name, LatencyBucket())
        self._latencies[name].record(latency_ms)

    # ── Counters ─────────────────────────────────────────────────────────────
    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += value

    # ── Snapshot ─────────────────────────────────────────────────────────────
    def snapshot(self) -> dict:
        snap: dict = {
            "active_sessions": self._active_sessions,
            "counters": dict(self._counters),
            "latencies": {},
        }
        for name, bucket in self._latencies.items():
            snap["latencies"][name] = {
                "avg_ms": round(bucket.avg(), 2),
                "p50_ms": round(bucket.percentile(50), 2),
                "p95_ms": round(bucket.percentile(95), 2),
                "p99_ms": round(bucket.percentile(99), 2),
            }
        return snap


metrics_registry = MetricsRegistry()


class LatencyTimer:
    """Context manager that records latency automatically."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._start: float = 0.0

    def __enter__(self) -> "LatencyTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_) -> None:
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        metrics_registry.record_latency(self.name, elapsed_ms)
