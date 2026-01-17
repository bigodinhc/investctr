"""
Celery task for parsing documents using Claude.
"""

import asyncio
from uuid import UUID

from app.core.logging import get_logger
from app.database import async_session_factory
from app.services.parsing_service import ParsingService
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="parse_document",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def parse_document(self, document_id: str, user_id: str) -> dict:
    """
    Celery task to parse a document using Claude.

    Args:
        document_id: String UUID of the document to parse
        user_id: String UUID of the document owner

    Returns:
        Dictionary with parsing results
    """
    logger.info(
        "task_parse_document_start",
        document_id=document_id,
        user_id=user_id,
        attempt=self.request.retries + 1,
    )

    async def _parse():
        async with async_session_factory() as session:
            service = ParsingService(session)
            try:
                result = await service.parse_document(
                    UUID(document_id),
                    UUID(user_id),
                )
                return {
                    "success": result.success,
                    "document_type": result.document_type,
                    "transaction_count": result.transaction_count,
                    "error": result.error,
                }
            except ValueError as e:
                # Don't retry for validation errors
                logger.warning(
                    "task_parse_document_validation_error",
                    document_id=document_id,
                    error=str(e),
                )
                return {
                    "success": False,
                    "document_type": None,
                    "transaction_count": 0,
                    "error": str(e),
                }

    try:
        # Run async code in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_parse())
        finally:
            loop.close()

        logger.info(
            "task_parse_document_complete",
            document_id=document_id,
            success=result["success"],
            transaction_count=result.get("transaction_count", 0),
        )

        return result

    except Exception as e:
        logger.error(
            "task_parse_document_error",
            document_id=document_id,
            error=str(e),
        )
        raise
