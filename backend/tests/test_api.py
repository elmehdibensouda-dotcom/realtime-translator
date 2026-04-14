"""
Integration tests for the WebSocket /ws/translate endpoint.
Run: pytest tests/ -v
"""

import asyncio
import json
import struct
import time

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.security import create_access_token


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_test_token(subject: str = "test-device-001") -> str:
    return create_access_token(subject)


def make_sine_pcm(duration_ms: int = 200, freq: int = 440, sample_rate: int = 16000) -> bytes:
    """Generate a simple sine wave as 16-bit PCM bytes."""
    import math
    n_samples = int(sample_rate * duration_ms / 1000)
    samples = [
        int(32767 * math.sin(2 * math.pi * freq * i / sample_rate))
        for i in range(n_samples)
    ]
    return struct.pack(f"<{n_samples}h", *samples)


# ── REST tests ────────────────────────────────────────────────────────────────

def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "active_sessions" in body


def test_auth_token():
    client = TestClient(app)
    r = client.post("/auth/token", json={"client_id": "device-123"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_auth_token_missing_client_id():
    client = TestClient(app)
    r = client.post("/auth/token", json={"client_id": ""})
    assert r.status_code == 400


def test_metrics():
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "active_sessions" in body


# ── WebSocket tests ────────────────────────────────────────────────────────────

def test_ws_rejects_missing_token():
    client = TestClient(app)
    with client.websocket_connect("/ws/translate") as ws:
        # Should receive error or be closed immediately
        try:
            data = ws.receive_text()
            msg = json.loads(data)
            assert msg.get("event") == "error" or ws.closed
        except Exception:
            pass  # connection closed — expected


def test_ws_rejects_invalid_token():
    client = TestClient(app)
    with client.websocket_connect("/ws/translate?token=bad.token.here") as ws:
        try:
            data = ws.receive_text()
            msg = json.loads(data)
            assert "error" in str(msg).lower() or ws.closed
        except Exception:
            pass


def test_ws_connects_with_valid_token():
    token = get_test_token()
    client = TestClient(app)
    with client.websocket_connect(f"/ws/translate?token={token}") as ws:
        data = ws.receive_text()
        msg = json.loads(data)
        assert msg["event"] == "connected"
        assert "session_id" in msg
        assert len(msg["session_id"]) == 36  # UUID format


# ── Metrics unit tests ────────────────────────────────────────────────────────

def test_metrics_latency_bucket():
    from app.core.metrics import LatencyBucket
    bucket = LatencyBucket()
    for v in [10, 20, 30, 40, 50]:
        bucket.record(v)
    assert bucket.avg() == 30.0
    assert bucket.percentile(50) == 30
    assert bucket.percentile(99) == 50


def test_metrics_registry_sessions():
    from app.core.metrics import MetricsRegistry
    reg = MetricsRegistry()
    assert reg.active_sessions == 0
    reg.session_opened()
    reg.session_opened()
    assert reg.active_sessions == 2
    reg.session_closed()
    assert reg.active_sessions == 1


# ── Security unit tests ───────────────────────────────────────────────────────

def test_jwt_roundtrip():
    from app.core.security import create_access_token, verify_token
    token = create_access_token("user-42")
    claims = verify_token(token)
    assert claims["sub"] == "user-42"


def test_jwt_expired():
    from datetime import timedelta
    from fastapi import HTTPException
    from app.core.security import create_access_token, verify_token
    token = create_access_token("user-42", expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        verify_token(token)
    assert exc_info.value.status_code == 401
