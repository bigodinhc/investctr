"""
Security utilities for JWT validation and authentication with Supabase.
"""

import time
from typing import Any
from uuid import UUID

import jwt
from jwt import PyJWKClient
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Cache for JWKS client
_jwks_client: PyJWKClient | None = None
_jwks_cache_time: float = 0
JWKS_CACHE_TTL = 3600  # 1 hour


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


def get_jwks_client() -> PyJWKClient | None:
    """
    Get or create a cached JWKS client for Supabase.
    Returns None if SUPABASE_URL is not configured.
    """
    global _jwks_client, _jwks_cache_time

    if not settings.supabase_url:
        return None

    # Check if cache is still valid
    if _jwks_client and (time.time() - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_client

    # Create new JWKS client
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        _jwks_client = PyJWKClient(jwks_url)
        _jwks_cache_time = time.time()
        logger.info("jwks_client_created", url=jwks_url)
        return _jwks_client
    except Exception as e:
        logger.warning("jwks_client_creation_failed", error=str(e))
        return None


def get_jwt_secret() -> str | None:
    """
    Get the JWT secret for token verification (legacy HS256).
    Returns None if not configured.
    """
    return settings.jwt_secret


def decode_supabase_jwt(token: str) -> dict[str, Any]:
    """
    Decode and validate a Supabase JWT token.
    Supports both RS256 (JWKS) and HS256 (legacy secret).

    Args:
        token: JWT token string from Supabase Auth

    Returns:
        Decoded token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    # First, try to get the token header to determine algorithm
    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "")
    except jwt.exceptions.DecodeError as e:
        raise AuthenticationError(f"Invalid token format: {e}")

    logger.debug("jwt_decode_attempt", algorithm=alg)

    # Try RS256 with JWKS first if algorithm is RS*
    if alg.startswith("RS"):
        jwks_client = get_jwks_client()
        if jwks_client:
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256", "RS384", "RS512"],
                    options={
                        "verify_exp": True,
                        "verify_iat": True,
                        "require": ["sub", "exp", "iat"],
                    },
                    audience="authenticated",
                )
                return payload
            except jwt.ExpiredSignatureError:
                raise AuthenticationError("Token has expired. Please log in again.")
            except jwt.InvalidAudienceError:
                raise AuthenticationError("Invalid token audience.")
            except jwt.InvalidTokenError as e:
                logger.warning("rs256_verification_failed", error=str(e))
                # Fall through to try HS256
            except Exception as e:
                logger.warning("jwks_verification_error", error=str(e))
                # Fall through to try HS256

    # Try HS256 with secret
    secret = get_jwt_secret()
    if secret:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256", "HS384", "HS512"],
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["sub", "exp", "iat"],
                },
                audience="authenticated",
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired. Please log in again.")
        except jwt.InvalidAudienceError:
            raise AuthenticationError("Invalid token audience.")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")

    # No verification method available
    raise AuthenticationError(
        "JWT verification not configured. "
        "Please set JWT_SECRET or SUPABASE_URL environment variable."
    )


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
