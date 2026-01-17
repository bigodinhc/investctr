"""
Document management endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import AuthenticatedUser, DBSession, Pagination
from app.config import settings
from app.core.logging import get_logger
from app.models import Document
from app.schemas.document import (
    DocumentParseRequest,
    DocumentResponse,
    DocumentsListResponse,
    DocumentWithData,
    ParseTaskResponse,
)
from app.schemas.enums import DocumentType, ParsingStatus

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

# Maximum file size: 20MB
MAX_FILE_SIZE = 20 * 1024 * 1024


@router.get("", response_model=DocumentsListResponse)
async def list_documents(
    user: AuthenticatedUser,
    db: DBSession,
    pagination: Pagination,
    status_filter: ParsingStatus | None = None,
) -> DocumentsListResponse:
    """List all documents for the authenticated user."""
    query = (
        select(Document)
        .where(Document.user_id == user.id)
        .offset(pagination.skip)
        .limit(pagination.limit)
        .order_by(Document.created_at.desc())
    )

    if status_filter:
        query = query.where(Document.parsing_status == status_filter)

    result = await db.execute(query)
    documents = result.scalars().all()

    # Get total count
    count_query = select(Document).where(Document.user_id == user.id)
    if status_filter:
        count_query = count_query.where(Document.parsing_status == status_filter)
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return DocumentsListResponse(
        items=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
    )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: AuthenticatedUser,
    db: DBSession,
    file: UploadFile = File(...),
    doc_type: DocumentType = Form(...),
    account_id: UUID | None = Form(None),
) -> DocumentResponse:
    """
    Upload a PDF document for parsing.

    The document will be stored in Supabase Storage and a record
    will be created in the database with status 'pending'.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed",
        )

    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed ({MAX_FILE_SIZE // (1024 * 1024)}MB)",
        )

    # Reset file pointer for storage upload
    await file.seek(0)

    # Generate storage path
    file_path = f"documents/{user.id}/{file.filename}"

    # Upload to Supabase Storage
    try:
        from app.integrations.supabase import upload_file_to_storage

        storage_path = await upload_file_to_storage(
            bucket="documents",
            path=file_path,
            content=content,
            content_type="application/pdf",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {str(e)}",
        )

    # Create document record
    document = Document(
        user_id=user.id,
        account_id=account_id,
        doc_type=doc_type,
        file_name=file.filename,
        file_path=storage_path,
        file_size=len(content),
        parsing_status=ParsingStatus.PENDING,
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    return DocumentResponse.model_validate(document)


@router.get("/{document_id}", response_model=DocumentWithData)
async def get_document(
    user: AuthenticatedUser,
    db: DBSession,
    document_id: UUID,
) -> DocumentWithData:
    """Get a specific document by ID, including parsed data if available."""
    query = (
        select(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == user.id)
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentWithData.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    user: AuthenticatedUser,
    db: DBSession,
    document_id: UUID,
) -> None:
    """Delete a document and its associated file from storage."""
    query = (
        select(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == user.id)
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Delete from storage
    try:
        from app.integrations.supabase import delete_file_from_storage

        await delete_file_from_storage(
            bucket="documents",
            path=document.file_path,
        )
    except Exception:
        # Log error but continue with database deletion
        pass

    await db.delete(document)
    await db.commit()


@router.post("/{document_id}/parse", response_model=ParseTaskResponse)
async def parse_document(
    user: AuthenticatedUser,
    db: DBSession,
    document_id: UUID,
    request: DocumentParseRequest | None = None,
) -> ParseTaskResponse:
    """
    Trigger parsing of a document.

    By default, parsing runs asynchronously via Celery.
    The document status will be updated to 'processing' immediately,
    and will change to 'completed' or 'failed' when parsing finishes.

    Args:
        document_id: UUID of the document to parse
        request: Optional configuration (async_mode defaults to True)

    Returns:
        ParseTaskResponse with task_id for tracking

    Raises:
        404: Document not found
        400: Document already parsed or currently processing
    """
    # Get document
    query = (
        select(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == user.id)
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if already parsed
    if document.parsing_status == ParsingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has already been parsed successfully",
        )

    # Check if currently processing
    if document.parsing_status == ParsingStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is currently being processed",
        )

    # Use async mode by default
    async_mode = True if request is None else request.async_mode

    logger.info(
        "parse_document_endpoint",
        document_id=str(document_id),
        user_id=str(user.id),
        async_mode=async_mode,
    )

    if async_mode:
        # Trigger Celery task
        from app.workers.tasks import parse_document as parse_task

        task = parse_task.delay(str(document_id), str(user.id))

        return ParseTaskResponse(
            document_id=document_id,
            task_id=task.id,
            status=ParsingStatus.PENDING,
            message="Parsing task queued successfully",
        )
    else:
        # Synchronous parsing (for testing/debugging)
        from app.services.parsing_service import ParsingService

        service = ParsingService(db)
        try:
            parse_result = await service.parse_document(document_id, user.id)

            return ParseTaskResponse(
                document_id=document_id,
                task_id="sync",
                status=ParsingStatus.COMPLETED if parse_result.success else ParsingStatus.FAILED,
                message=parse_result.error or f"Parsed {parse_result.transaction_count} transactions",
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            logger.error(
                "parse_document_sync_error",
                document_id=str(document_id),
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Parsing failed: {str(e)}",
            )


@router.post("/{document_id}/reparse", response_model=ParseTaskResponse)
async def reparse_document(
    user: AuthenticatedUser,
    db: DBSession,
    document_id: UUID,
) -> ParseTaskResponse:
    """
    Re-parse a document that was previously parsed or failed.

    This resets the document status and triggers a new parsing task.
    """
    # Get document
    query = (
        select(Document)
        .where(Document.id == document_id)
        .where(Document.user_id == user.id)
    )
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check if currently processing
    if document.parsing_status == ParsingStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is currently being processed",
        )

    # Reset status to pending
    document.parsing_status = ParsingStatus.PENDING
    document.parsing_error = None
    document.raw_extracted_data = None
    document.parsed_at = None
    await db.commit()

    logger.info(
        "reparse_document_endpoint",
        document_id=str(document_id),
        user_id=str(user.id),
    )

    # Trigger Celery task
    from app.workers.tasks import parse_document as parse_task

    task = parse_task.delay(str(document_id), str(user.id))

    return ParseTaskResponse(
        document_id=document_id,
        task_id=task.id,
        status=ParsingStatus.PENDING,
        message="Re-parsing task queued successfully",
    )
