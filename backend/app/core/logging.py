"""
Structured logging configuration using structlog.

Provides:
- Environment-aware formatting (dev: colored console, prod: JSON)
- Request context (request_id, user_id) propagation
- get_logger() for module-level loggers
- log_context() for adding context to all logs in current async context
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import Processor

from app.config import settings

# Context variables for request-scoped data
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)


def add_request_context(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add request context (request_id, user_id) to log events."""
    request_id = request_id_ctx.get()
    user_id = user_id_ctx.get()

    if request_id:
        event_dict["request_id"] = request_id
    if user_id:
        event_dict["user_id"] = user_id

    return event_dict


def setup_logging() -> None:
    """Configure structured logging for the application.

    In development: Pretty colored console output
    In production: JSON formatted logs for log aggregation systems
    """

    # Shared processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        add_request_context,  # Add request_id and user_id
    ]

    if settings.is_development:
        # Development: pretty console output with colors
        processors: list[Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output for log aggregation (ELK, Datadog, etc.)
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    log_level = logging.DEBUG if settings.debug else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,  # Override any existing config
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (typically __name__ from the calling module)

    Returns:
        A bound structlog logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("user_logged_in", user_id="123", email="user@example.com")
    """
    return structlog.get_logger(name)


def log_context(**kwargs: Any) -> None:
    """Add context variables to all subsequent log calls in this async context.

    These values will be included in every log message until cleared or
    the async context ends.

    Example:
        log_context(user_id="123", account_id="456")
        logger.info("processing_request")  # Will include user_id and account_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_log_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()


def set_request_context(
    request_id: str | None = None, user_id: str | None = None
) -> None:
    """Set request-scoped context variables.

    These are stored in ContextVars and automatically included in all
    log entries during the request lifecycle.

    Args:
        request_id: Unique identifier for the request (correlation ID)
        user_id: ID of the authenticated user (if any)
    """
    if request_id:
        request_id_ctx.set(request_id)
    if user_id:
        user_id_ctx.set(user_id)


def generate_request_id() -> str:
    """Generate a unique request ID for correlation.

    Uses a short UUID format for readability in logs.
    """
    return str(uuid.uuid4())[:8]


def clear_request_context() -> None:
    """Clear request-scoped context variables."""
    request_id_ctx.set(None)
    user_id_ctx.set(None)
