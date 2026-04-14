"""JWT generation & validation helpers."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

_ALGORITHM = settings.JWT_ALGORITHM
_SECRET = settings.SECRET_KEY


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}"
        )


def extract_token_from_query(token: Optional[str]) -> dict:
    """Used for WebSocket auth (token passed as query param)."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token"
        )
    return verify_token(token)
