"""
Security utilities for JWT validation and authentication.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

import jwt
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import AuthenticationError


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # User ID
    email: str | None = None
    exp: datetime
    iat: datetime
    aud: str | None = None
    role: str | None = None


class CurrentUser(BaseModel):
    """Authenticated user information."""

    id: UUID
    email: str | None = None
    role: str | None = None


def decode_jwt(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    if not settings.jwt_secret:
        raise AuthenticationError("JWT secret not configured")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={
                "verify_exp": True,
                "verify_iat": True,
                "require": ["sub", "exp", "iat"],
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {e}")


def get_user_from_token(token: str) -> CurrentUser:
    """
    Extract user information from a JWT token.

    Args:
        token: JWT token string

    Returns:
        CurrentUser with user information

    Raises:
        AuthenticationError: If token is invalid
    """
    payload = decode_jwt(token)

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise AuthenticationError("Invalid user ID in token")

    return CurrentUser(
        id=user_id,
        email=payload.get("email"),
        role=payload.get("role"),
    )


def extract_token_from_header(authorization: str | None) -> str:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value

    Returns:
        JWT token string

    Raises:
        AuthenticationError: If header is missing or malformed
    """
    if not authorization:
        raise AuthenticationError("Authorization header missing")

    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization header format")

    return parts[1]
