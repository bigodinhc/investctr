"""
Sentry SDK configuration for error monitoring.

Integrates with FastAPI and Celery for comprehensive error tracking.
"""

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> bool:
    """
    Initialize Sentry SDK for error monitoring.

    Returns True if Sentry was initialized successfully, False otherwise.
    Silently skips initialization if SENTRY_DSN is not configured.
    """
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not configured, skipping Sentry initialization")
        return False

    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            release=f"investctr-backend@{settings.app_version}",

            # Sample rates
            traces_sample_rate=1.0 if settings.is_development else 0.1,
            profiles_sample_rate=1.0 if settings.is_development else 0.1,

            # Integrations
            integrations=[
                StarletteIntegration(
                    transaction_style="endpoint",
                ),
                FastApiIntegration(
                    transaction_style="endpoint",
                ),
                CeleryIntegration(
                    monitor_beat_tasks=True,
                    propagate_traces=True,
                ),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
            ],

            # Performance monitoring
            enable_tracing=True,

            # Data scrubbing - remove sensitive data
            send_default_pii=False,

            # Additional options
            attach_stacktrace=True,
            include_local_variables=settings.is_development,

            # Filter events before sending
            before_send=before_send_filter,
        )

        # Set user context (will be overwritten per-request)
        sentry_sdk.set_context("app", {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        })

        logger.info(
            f"Sentry initialized successfully for environment: {settings.environment}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def before_send_filter(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """
    Filter events before sending to Sentry.

    Use this to scrub sensitive data or drop certain events.
    """
    # Don't send health check endpoint errors
    if event.get("request", {}).get("url", "").endswith("/health"):
        return None

    # Remove sensitive headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[Filtered]"

    return event


def capture_exception_with_context(
    exception: Exception,
    user_id: str | None = None,
    extra_context: dict[str, Any] | None = None,
) -> str | None:
    """
    Capture an exception with additional context.

    Args:
        exception: The exception to capture
        user_id: Optional user ID for context
        extra_context: Optional additional context dict

    Returns:
        The Sentry event ID if captured, None otherwise
    """
    if not settings.sentry_dsn:
        return None

    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_user({"id": user_id})

        if extra_context:
            for key, value in extra_context.items():
                scope.set_extra(key, value)

        return sentry_sdk.capture_exception(exception)


def capture_message_with_context(
    message: str,
    level: str = "info",
    user_id: str | None = None,
    extra_context: dict[str, Any] | None = None,
) -> str | None:
    """
    Capture a message with additional context.

    Args:
        message: The message to capture
        level: Log level (debug, info, warning, error, fatal)
        user_id: Optional user ID for context
        extra_context: Optional additional context dict

    Returns:
        The Sentry event ID if captured, None otherwise
    """
    if not settings.sentry_dsn:
        return None

    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_user({"id": user_id})

        if extra_context:
            for key, value in extra_context.items():
                scope.set_extra(key, value)

        return sentry_sdk.capture_message(message, level=level)


def set_user_context(user_id: str, email: str | None = None) -> None:
    """
    Set user context for Sentry events.

    Should be called after user authentication.
    """
    if not settings.sentry_dsn:
        return

    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
    })


def clear_user_context() -> None:
    """Clear user context from Sentry scope."""
    if not settings.sentry_dsn:
        return

    sentry_sdk.set_user(None)
