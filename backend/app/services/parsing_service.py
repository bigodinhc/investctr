"""
Document parsing service - orchestrates the parsing workflow.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.integrations.claude.parsers import (
    ParseResult,
    StatementParser,
    TradeNoteParser,
)
from app.integrations.supabase import get_file_from_storage
from app.models import Document
from app.schemas.enums import DocumentType, ParsingStatus
from app.services.validation import ValidationService

logger = get_logger(__name__)


class ParsingService:
    """Service for parsing documents using Claude."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.validation_service = ValidationService()

    async def get_document(self, document_id: UUID, user_id: UUID) -> Document | None:
        """Get a document by ID and user ID."""
        query = (
            select(Document)
            .where(Document.id == document_id)
            .where(Document.user_id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def parse_document(self, document_id: UUID, user_id: UUID) -> ParseResult:
        """
        Parse a document and store the results.

        Args:
            document_id: UUID of the document to parse
            user_id: UUID of the document owner

        Returns:
            ParseResult with extracted data

        Raises:
            ValueError: If document not found or already parsed
        """
        # Get document
        document = await self.get_document(document_id, user_id)
        if not document:
            raise ValueError("Document not found")

        if document.parsing_status == ParsingStatus.COMPLETED:
            raise ValueError("Document already parsed")

        if document.parsing_status == ParsingStatus.PROCESSING:
            raise ValueError("Document is currently being processed")

        logger.info(
            "parsing_service_start",
            document_id=str(document_id),
            doc_type=document.doc_type,
        )

        # Update status to processing
        document.parsing_status = ParsingStatus.PROCESSING
        await self.db.commit()

        try:
            # Download PDF from storage
            pdf_content = await get_file_from_storage(
                bucket="documents",
                path=document.file_path,
            )

            # Select parser based on document type
            parser = self._get_parser(document.doc_type)

            # Parse the document
            result = await parser.parse(pdf_content)

            # Update document with results
            if result.success:
                # Validate and normalize the extracted data
                validated_data, validation_errors = self.validation_service.validate_statement_data(
                    result.raw_data
                )

                if validation_errors:
                    logger.warning(
                        "parsing_validation_warnings",
                        document_id=str(document_id),
                        errors=validation_errors,
                    )

                # Count transactions
                txn_count, count_warnings = self.validation_service.validate_and_count_transactions(
                    result.raw_data
                )

                # Extract summary
                summary = self.validation_service.extract_summary(result.raw_data)

                # Store validated data if validation succeeded, otherwise raw data
                document.parsing_status = ParsingStatus.COMPLETED
                document.raw_extracted_data = validated_data if validated_data else result.raw_data
                document.parsed_at = datetime.utcnow()
                document.parsing_error = None

                # Update result with accurate transaction count
                result = ParseResult(
                    success=True,
                    document_type=result.document_type,
                    raw_data=validated_data if validated_data else result.raw_data,
                    transactions=result.transactions,
                    error=None,
                    _transaction_count=txn_count,
                )

                logger.info(
                    "parsing_service_success",
                    document_id=str(document_id),
                    transaction_count=txn_count,
                    summary=summary,
                )
            else:
                document.parsing_status = ParsingStatus.FAILED
                document.parsing_error = result.error
                document.parsed_at = datetime.utcnow()

                logger.warning(
                    "parsing_service_failed",
                    document_id=str(document_id),
                    error=result.error,
                )

            await self.db.commit()
            return result

        except Exception as e:
            # Mark as failed
            document.parsing_status = ParsingStatus.FAILED
            document.parsing_error = str(e)
            document.parsed_at = datetime.utcnow()
            await self.db.commit()

            logger.error(
                "parsing_service_error",
                document_id=str(document_id),
                error=str(e),
            )

            return ParseResult(
                success=False,
                document_type=document.doc_type,
                raw_data={},
                error=str(e),
            )

    def _get_parser(self, doc_type: DocumentType):
        """Get the appropriate parser for the document type."""
        parsers = {
            DocumentType.STATEMENT: StatementParser,
            DocumentType.TRADE_NOTE: TradeNoteParser,
        }

        parser_class = parsers.get(doc_type)
        if not parser_class:
            raise ValueError(f"No parser available for document type: {doc_type}")

        return parser_class()


async def parse_document_sync(
    document_id: str,
    user_id: str,
) -> dict[str, Any]:
    """
    Synchronous wrapper for document parsing (for Celery tasks).

    Args:
        document_id: String UUID of the document
        user_id: String UUID of the user

    Returns:
        Dictionary with parsing results
    """
    import asyncio

    from app.database import async_session_factory

    async def _parse():
        async with async_session_factory() as session:
            service = ParsingService(session)
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

    return asyncio.get_event_loop().run_until_complete(_parse())
