"""
Security utilities for JWT validation and authentication with Supabase.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

import jwt
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import AuthenticationError


class TokenPayload(BaseModel):
    """JWT token payload from Supabase."""

    sub: str  # User ID (UUID)
    email: str | None = None
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    aud: str | None = None  # Audience (usually "authenticated")
    role: str | None = None  # Supabase role
    aal: str | None = None  # Authentication Assurance Level
    amr: list[dict] | None = None  # Authentication Methods Reference
    session_id: str | None = None


class CurrentUser(BaseModel):
    """Authenticated user information extracted from JWT."""

    id: UUID
    email: str | None = None
    role: str | None = None
    aal: str | None = None  # "aal1" or "aal2" (MFA)

    class Config:
        frozen = True


def get_jwt_secret() -> str:
    """
    Get the JWT secret for token verification.

    For Supabase, this is the JWT secret from Project Settings > API.
    """
    if settings.jwt_secret:
        return settings.jwt_secret

    # Fallback: try to derive from Supabase URL (not recommended for production)
    raise AuthenticationError(
        "JWT_SECRET is not configured. "
        "Please set it from Supabase Project Settings > API > JWT Secret."
    )


def decode_supabase_jwt(token: str) -> dict[str, Any]:
    """
    Decode and validate a Supabase JWT token.

    Args:
        token: JWT token string from Supabase Auth

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        secret = get_jwt_secret()

        # Supabase uses HS256 by default, but may use other HS algorithms
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256", "HS384", "HS512"],
            options={
                "verify_exp": True,
                "verify_iat": True,
                "require": ["sub", "exp", "iat"],
            },
            # Supabase sets audience to "authenticated" for logged-in users
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired. Please log in again.")
    except jwt.InvalidAudienceError:
        raise AuthenticationError("Invalid token audience.")
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {e}")


def get_user_from_token(token: str) -> CurrentUser:
    """
    Extract user information from a Supabase JWT token.

    Args:
        token: JWT token string

    Returns:
        CurrentUser with user information

    Raises:
        AuthenticationError: If token is invalid
    """
    payload = decode_supabase_jwt(token)

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, KeyError):
        raise AuthenticationError("Invalid user ID in token")

    return CurrentUser(
        id=user_id,
        email=payload.get("email"),
        role=payload.get("role"),
        aal=payload.get("aal"),
    )


def extract_token_from_header(authorization: str | None) -> str:
    """
    Extract JWT token from Authorization header.

    Args:
        authorization: Authorization header value (Bearer <token>)

    Returns:
        JWT token string

    Raises:
        AuthenticationError: If header is missing or malformed
    """
    if not authorization:
        raise AuthenticationError("Authorization header is required")

    parts = authorization.split()

    if len(parts) != 2:
        raise AuthenticationError(
            "Invalid authorization header format. Expected: Bearer <token>"
        )

    scheme, token = parts

    if scheme.lower() != "bearer":
        raise AuthenticationError(
            f"Invalid authentication scheme: {scheme}. Expected: Bearer"
        )

    return token


def verify_token(token: str) -> CurrentUser:
    """
    Verify a JWT token and return the authenticated user.

    This is a convenience function that combines token extraction
    and user retrieval.

    Args:
        token: JWT token string

    Returns:
        CurrentUser with user information

    Raises:
        AuthenticationError: If token is invalid
    """
    return get_user_from_token(token)
