"""Bearer authentication for sensitive API routes."""
import hmac
import os
from typing import Optional
from fastapi import Header, HTTPException


def require_api_token(authorization: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("API_TOKEN", "")
    if not expected or expected.startswith(("replace-with", "change-me")):
        raise HTTPException(status_code=503, detail="API_TOKEN is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    supplied = authorization[len("Bearer "):]
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=401, detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
