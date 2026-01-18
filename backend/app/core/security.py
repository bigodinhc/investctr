"""
Security utilities for JWT validation and authentication with Supabase.
"""

import time
from typing import Any
from uuid import UUID

import jwt
from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Cache for JWKS client
_jwks_client = None
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


def get_jwks_client():
    """
    Get or create a cached JWKS client for Supabase.
    Returns None if SUPABASE_URL is not configured.
    """
    global _jwks_client, _jwks_cache_time

    from jwt import PyJWKClient

    if not settings.supabase_url:
        logger.warning("supabase_url_not_configured")
        return None

    # Check if cache is still valid
    if _jwks_client and (time.time() - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_client

    # Create new JWKS client
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    logger.info("creating_jwks_client", url=jwks_url)

    try:
        _jwks_client = PyJWKClient(jwks_url)
        _jwks_cache_time = time.time()
        logger.info("jwks_client_created_successfully")
        return _jwks_client
    except Exception as e:
        logger.error(
            "jwks_client_creation_failed", error=str(e), error_type=type(e).__name__
        )
        return None


def decode_supabase_jwt(token: str) -> dict[str, Any]:
    """
    Decode and validate a Supabase JWT token.
    Supports both RS256 (JWKS) and HS256 (legacy secret).
    """
    # First, decode without verification to see the algorithm
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "unknown")
        logger.info(
            "jwt_token_info",
            algorithm=alg,
            has_sub="sub" in unverified,
            has_aud="aud" in unverified,
            aud=unverified.get("aud"),
        )
    except Exception as e:
        logger.error("jwt_decode_unverified_failed", error=str(e))
        raise AuthenticationError(f"Invalid token format: {e}")

    # Route based on algorithm
    # RSA algorithms (RS256, RS384, RS512) and EC algorithms (ES256, ES384, ES512) use JWKS
    if alg in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512"):
        logger.info("attempting_jwks_verification", algorithm=alg)
        jwks_client = get_jwks_client()

        if jwks_client:
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                logger.info("got_signing_key_from_jwks")

                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=[alg],
                    audience="authenticated",
                )
                logger.info("jwks_verification_successful", algorithm=alg)
                return payload

            except jwt.ExpiredSignatureError:
                raise AuthenticationError("Token has expired. Please log in again.")
            except jwt.InvalidAudienceError as e:
                logger.error("invalid_audience", error=str(e), expected="authenticated")
                raise AuthenticationError("Invalid token audience.")
            except Exception as e:
                logger.error(
                    "jwks_verification_failed",
                    algorithm=alg,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise AuthenticationError(f"Token verification failed: {e}")
        else:
            raise AuthenticationError(
                f"Token uses {alg} algorithm but SUPABASE_URL is not configured for JWKS verification."
            )

    elif alg in ("HS256", "HS384", "HS512"):
        logger.info("attempting_hs256_verification")
        secret = settings.jwt_secret

        if not secret:
            raise AuthenticationError(
                f"Token uses {alg} algorithm but JWT_SECRET is not configured."
            )

        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[alg],
                audience="authenticated",
            )
            logger.info("hs256_verification_successful")
            return payload

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired. Please log in again.")
        except jwt.InvalidAudienceError as e:
            logger.error("invalid_audience", error=str(e), expected="authenticated")
            raise AuthenticationError("Invalid token audience.")
        except Exception as e:
            logger.error(
                "hs256_verification_failed", error=str(e), error_type=type(e).__name__
            )
            raise AuthenticationError(f"Token verification failed: {e}")

    else:
        raise AuthenticationError(f"Unsupported JWT algorithm: {alg}")


def get_user_from_token(token: str) -> CurrentUser:
    """
    Extract user information from a Supabase JWT token.
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
    """
    return get_user_from_token(token)
