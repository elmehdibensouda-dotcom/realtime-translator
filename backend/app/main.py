"""
RealtimeTranslator - FastAPI Backend
Streaming ASR (Deepgram) + Translation (DeepL) via WebSocket
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.metrics import metrics_registry

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 RealtimeTranslator backend starting...")
    logger.info("   Mode          : FREE (Web Speech API + Google)")
    logger.info(f"   Max workers   : {settings.FREE_TRANSLATION_MAX_WORKERS}")
    logger.info(f"   Max sessions  : {settings.MAX_CONCURRENT_SESSIONS}")
    yield
    logger.info("🛑 Backend shutting down...")


app = FastAPI(
    title="RealtimeTranslator API",
    description="Real-time voice transcription & translation (EN→FR)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ── Middleware ───────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "version": "1.0.0",
        "active_sessions": metrics_registry.active_sessions,
    }


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    return metrics_registry.snapshot()
