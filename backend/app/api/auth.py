"""
Auth REST endpoint – issues JWT tokens for mobile clients.
In production, integrate with your identity provider (Auth0, Firebase, etc.)
"""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class TokenRequest(BaseModel):
    client_id: str       # Device ID or anonymous UUID
    secret: str = ""     # Extend with real auth as needed


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


@router.post("/token", response_model=TokenResponse)
async def get_token(body: TokenRequest) -> TokenResponse:
    """
    Issue a short-lived JWT.
    Add real credential validation here (API key, user login, etc.).
    """
    if not body.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_id required",
        )

    token = create_access_token(
        subject=body.client_id,
        expires_delta=timedelta(hours=1),
    )
    return TokenResponse(access_token=token, expires_in=3600)
