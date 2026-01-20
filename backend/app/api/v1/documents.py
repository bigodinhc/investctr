"""
Document management endpoints.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select

from app.api.deps import AuthenticatedUser, DBSession, Pagination
from app.core.logging import get_logger
from app.core.rate_limit import rate_limit
from app.models import (
    Account,
    Asset,
    CashFlow,
    Document,
    FixedIncomePosition,
    Transaction,
)
from app.schemas.document import (
    DocumentParseRequest,
    DocumentResponse,
    DocumentsListResponse,
    DocumentWithData,
    ParseTaskResponse,
)
from app.schemas.enums import (
    AssetType,
    CashFlowType,
    DocumentType,
    FixedIncomeType,
    IndexerType,
    ParsingStatus,
    TransactionType,
)
from app.schemas.transaction import CommitDocumentRequest, CommitDocumentResponse
from app.services.position_service import PositionService

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


@router.post(
    "/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
@rate_limit(requests=10, window=60, group="upload")
async def upload_document(
    request: Request,
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
@rate_limit(requests=5, window=60, group="parse")
async def parse_document(
    request: Request,
    user: AuthenticatedUser,
    db: DBSession,
    document_id: UUID,
    parse_request: DocumentParseRequest | None = None,
) -> ParseTaskResponse:
    """
    Trigger parsing of a document.

    By default, parsing runs asynchronously via Celery.
    The document status will be updated to 'processing' immediately,
    and will change to 'completed' or 'failed' when parsing finishes.

    Rate limited to 5 requests/minute (Claude API).

    Args:
        document_id: UUID of the document to parse
        parse_request: Optional configuration (async_mode defaults to True)

    Returns:
        ParseTaskResponse with task_id for tracking

    Raises:
        404: Document not found
        400: Document already parsed or currently processing
        429: Rate limit exceeded
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
    async_mode = True if parse_request is None else parse_request.async_mode

    logger.info(
        "parse_document_endpoint",
        document_id=str(document_id),
        user_id=str(user.id),
        async_mode=async_mode,
    )

    # Check if Celery/Redis is configured before attempting async mode
    from app.config import get_settings

    celery_configured = bool(get_settings().celery_broker_url)

    if async_mode and celery_configured:
        # Try to trigger Celery task
        try:
            from app.workers.tasks import parse_document as parse_task

            task = parse_task.delay(str(document_id), str(user.id))

            return ParseTaskResponse(
                document_id=document_id,
                task_id=task.id,
                status=ParsingStatus.PENDING,
                message="Parsing task queued successfully",
            )
        except Exception as celery_error:
            # Redis/Celery not available, fallback to synchronous parsing
            logger.warning(
                "celery_unavailable_fallback_sync",
                document_id=str(document_id),
                error=str(celery_error),
            )
            # Continue to synchronous parsing below
            async_mode = False
    elif async_mode and not celery_configured:
        # Celery not configured, use sync mode
        logger.info(
            "celery_not_configured_using_sync",
            document_id=str(document_id),
        )
        async_mode = False

    if not async_mode:
        # Synchronous parsing (fallback or explicit)
        from app.services.parsing_service import ParsingService

        service = ParsingService(db)
        try:
            parse_result = await service.parse_document(document_id, user.id)

            return ParseTaskResponse(
                document_id=document_id,
                task_id="sync",
                status=ParsingStatus.COMPLETED
                if parse_result.success
                else ParsingStatus.FAILED,
                message=parse_result.error
                or f"Parsed {parse_result.transaction_count} transactions",
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


@router.get("/{document_id}/parse-result")
async def get_parse_result(
    user: AuthenticatedUser,
    db: DBSession,
    document_id: UUID,
) -> dict:
    """
    Get the parsing result for a document.

    Used for polling the status of async parsing tasks.
    Returns the current parsing status and extracted data if available.
    """
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

    # Build response - return raw data directly to avoid validation issues
    parsed_data = None
    transactions_count = 0

    if document.raw_extracted_data:
        raw_data = document.raw_extracted_data
        transactions_count = len(raw_data.get("transactions", []))
        parsed_data = {
            "document_type": raw_data.get("document_type", "unknown"),
            "period": raw_data.get("period"),
            "account_number": raw_data.get("account_number"),
            "transactions": raw_data.get("transactions", []),
            "summary": raw_data.get("summary"),
            "fixed_income_positions": raw_data.get("fixed_income_positions"),
            "stock_lending": raw_data.get("stock_lending"),
            "cash_movements": raw_data.get("cash_movements"),
            "consolidated_position": raw_data.get("consolidated_position"),
        }

    return {
        "document_id": str(document.id),
        "status": document.parsing_status.value if document.parsing_status else None,
        "stage": document.parsing_stage,
        "transactions_count": transactions_count,
        "data": parsed_data,
        "error": document.parsing_error,
    }


@router.post("/{document_id}/reparse", response_model=ParseTaskResponse)
@rate_limit(requests=5, window=60, group="parse")
async def reparse_document(
    request: Request,
    user: AuthenticatedUser,
    db: DBSession,
    document_id: UUID,
) -> ParseTaskResponse:
    """
    Re-parse a document that was previously parsed or failed.

    This resets the document status and triggers a new parsing task.

    Rate limited to 5 requests/minute (Claude API).
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

    # Check if Celery/Redis is configured
    from app.config import get_settings

    celery_configured = bool(get_settings().celery_broker_url)

    if celery_configured:
        # Try to trigger Celery task
        try:
            from app.workers.tasks import parse_document as parse_task

            task = parse_task.delay(str(document_id), str(user.id))

            return ParseTaskResponse(
                document_id=document_id,
                task_id=task.id,
                status=ParsingStatus.PENDING,
                message="Re-parsing task queued successfully",
            )
        except Exception as celery_error:
            # Redis/Celery not available, fallback to synchronous parsing
            logger.warning(
                "celery_unavailable_fallback_sync_reparse",
                document_id=str(document_id),
                error=str(celery_error),
            )

    # Synchronous parsing (Celery not configured or failed)
    from app.services.parsing_service import ParsingService

    service = ParsingService(db)
    try:
        parse_result = await service.parse_document(document_id, user.id)

        return ParseTaskResponse(
            document_id=document_id,
            task_id="sync",
            status=ParsingStatus.COMPLETED
            if parse_result.success
            else ParsingStatus.FAILED,
            message=parse_result.error
            or f"Re-parsed {parse_result.transaction_count} transactions",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "reparse_document_sync_error",
            document_id=str(document_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-parsing failed: {str(e)}",
        )


@router.post("/{document_id}/commit", response_model=CommitDocumentResponse)
async def commit_document_transactions(
    user: AuthenticatedUser,
    db: DBSession,
    document_id: UUID,
    request: CommitDocumentRequest,
) -> CommitDocumentResponse:
    """
    Commit parsed document data to the database.

    This endpoint takes the parsed data (reviewed/edited by user)
    and creates database records. It handles:
    - Transactions (buy/sell) → transactions table
    - Stock lending → transactions table (type=rental)
    - Fixed income positions → fixed_income_positions table
    - Cash movements → cash_flows table
    - Asset auto-creation if they don't exist
    - Position recalculation for affected assets

    Args:
        document_id: UUID of the parsed document
        request: CommitDocumentRequest with account_id and data lists

    Returns:
        CommitDocumentResponse with counts of created records

    Raises:
        404: Document not found
        400: Document not parsed yet or account doesn't belong to user
    """
    # Validate document exists and belongs to user
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

    # Document must be parsed first
    if document.parsing_status != ParsingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document must be successfully parsed before committing",
        )

    # Validate account belongs to user
    account_query = (
        select(Account)
        .where(Account.id == request.account_id)
        .where(Account.user_id == user.id)
    )
    account_result = await db.execute(account_query)
    account = account_result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account not found or doesn't belong to user",
        )

    logger.info(
        "commit_document_start",
        document_id=str(document_id),
        user_id=str(user.id),
        account_id=str(request.account_id),
        transaction_count=len(request.transactions),
        fixed_income_count=len(request.fixed_income),
        stock_lending_count=len(request.stock_lending),
        cash_movements_count=len(request.cash_movements),
    )

    errors: list[str] = []
    transactions_created = 0
    assets_created = 0
    fixed_income_created = 0
    cash_flows_created = 0
    asset_ids_to_recalculate: set[UUID] = set()

    # =====================================================================
    # Process transactions (buy/sell)
    # =====================================================================
    for idx, txn_data in enumerate(request.transactions):
        try:
            # Get or create asset
            asset, was_created = await _get_or_create_asset(
                db=db,
                ticker=txn_data.ticker,
                asset_name=txn_data.asset_name,
                asset_type_str=txn_data.asset_type,
            )
            if was_created:
                assets_created += 1

            # Map transaction type
            txn_type = _map_transaction_type(txn_data.type)

            # Calculate values
            quantity = txn_data.quantity or Decimal("0")
            price = txn_data.price or Decimal("0")
            total = txn_data.total or (quantity * price)
            fees = txn_data.fees or Decimal("0")

            # Infer price from total if not provided
            if price == Decimal("0") and quantity > 0 and total > 0:
                price = total / quantity

            # Parse date
            try:
                executed_at = datetime.strptime(txn_data.date, "%Y-%m-%d")
            except ValueError:
                errors.append(
                    f"Transaction {idx + 1}: Invalid date format '{txn_data.date}'"
                )
                continue

            # Create transaction
            transaction = Transaction(
                account_id=request.account_id,
                asset_id=asset.id,
                document_id=document_id,
                type=txn_type,
                quantity=quantity,
                price=price,
                fees=fees,
                executed_at=executed_at,
                notes=txn_data.notes,
            )

            db.add(transaction)
            transactions_created += 1
            asset_ids_to_recalculate.add(asset.id)

        except Exception as e:
            errors.append(f"Transaction {idx + 1} ({txn_data.ticker}): {str(e)}")
            logger.warning(
                "commit_transaction_error",
                document_id=str(document_id),
                transaction_idx=idx,
                ticker=txn_data.ticker,
                error=str(e),
            )

    # =====================================================================
    # Process stock lending
    # =====================================================================
    for idx, lending_data in enumerate(request.stock_lending):
        try:
            # Get or create asset
            asset, was_created = await _get_or_create_asset(
                db=db,
                ticker=lending_data.ticker,
                asset_name=None,
                asset_type_str=None,
            )
            if was_created:
                assets_created += 1

            # Parse date
            try:
                executed_at = datetime.strptime(lending_data.date, "%Y-%m-%d")
            except ValueError:
                errors.append(
                    f"Stock lending {idx + 1}: Invalid date format '{lending_data.date}'"
                )
                continue

            # Calculate price from total/quantity for rental income
            quantity = lending_data.quantity
            total = lending_data.total
            price = total / quantity if quantity > 0 else Decimal("0")

            # Build notes with rate info
            notes = lending_data.notes or ""
            if lending_data.rate_percent:
                notes = f"Taxa: {lending_data.rate_percent}%. {notes}".strip()
            if lending_data.type:
                notes = f"Tipo: {lending_data.type}. {notes}".strip()

            # Create transaction as rental
            transaction = Transaction(
                account_id=request.account_id,
                asset_id=asset.id,
                document_id=document_id,
                type=TransactionType.RENTAL,
                quantity=quantity,
                price=price,
                fees=Decimal("0"),
                executed_at=executed_at,
                notes=notes,
            )

            db.add(transaction)
            transactions_created += 1

        except Exception as e:
            errors.append(f"Stock lending {idx + 1} ({lending_data.ticker}): {str(e)}")
            logger.warning(
                "commit_stock_lending_error",
                document_id=str(document_id),
                idx=idx,
                ticker=lending_data.ticker,
                error=str(e),
            )

    # =====================================================================
    # Process fixed income positions
    # =====================================================================
    for idx, fi_data in enumerate(request.fixed_income):
        try:
            # Parse dates
            reference_date = None
            acquisition_date = None
            maturity_date = None

            try:
                reference_date = datetime.strptime(
                    fi_data.reference_date, "%Y-%m-%d"
                ).date()
            except ValueError:
                errors.append(
                    f"Fixed income {idx + 1}: Invalid reference_date format '{fi_data.reference_date}'"
                )
                continue

            if fi_data.acquisition_date:
                try:
                    acquisition_date = datetime.strptime(
                        fi_data.acquisition_date, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass  # Optional field, ignore invalid

            if fi_data.maturity_date:
                try:
                    maturity_date = datetime.strptime(
                        fi_data.maturity_date, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass  # Optional field, ignore invalid

            # Map asset type
            asset_type = _map_fixed_income_type(fi_data.asset_type)

            # Map indexer
            indexer = _map_indexer_type(fi_data.indexer) if fi_data.indexer else None

            # Create fixed income position
            fi_position = FixedIncomePosition(
                account_id=request.account_id,
                document_id=document_id,
                asset_name=fi_data.asset_name,
                asset_type=asset_type,
                issuer=fi_data.issuer,
                quantity=fi_data.quantity,
                unit_price=fi_data.unit_price,
                total_value=fi_data.total_value,
                indexer=indexer,
                rate_percent=fi_data.rate_percent,
                acquisition_date=acquisition_date,
                maturity_date=maturity_date,
                reference_date=reference_date,
            )

            db.add(fi_position)
            fixed_income_created += 1

        except Exception as e:
            errors.append(f"Fixed income {idx + 1} ({fi_data.asset_name}): {str(e)}")
            logger.warning(
                "commit_fixed_income_error",
                document_id=str(document_id),
                idx=idx,
                asset_name=fi_data.asset_name,
                error=str(e),
            )

    # =====================================================================
    # Process cash movements
    # =====================================================================
    for idx, cash_data in enumerate(request.cash_movements):
        try:
            # Parse date
            try:
                executed_at = datetime.strptime(cash_data.date, "%Y-%m-%d")
            except ValueError:
                errors.append(
                    f"Cash movement {idx + 1}: Invalid date format '{cash_data.date}'"
                )
                continue

            # Map cash flow type
            cf_type = _map_cash_flow_type(cash_data.type)

            # Build notes
            notes = cash_data.description or ""
            if cash_data.ticker:
                notes = f"Ticker: {cash_data.ticker}. {notes}".strip()

            # Create cash flow
            cash_flow = CashFlow(
                account_id=request.account_id,
                type=cf_type,
                amount=cash_data.value,
                currency="BRL",
                exchange_rate=Decimal("1"),
                executed_at=executed_at,
                notes=notes,
            )

            db.add(cash_flow)
            cash_flows_created += 1

        except Exception as e:
            errors.append(f"Cash movement {idx + 1}: {str(e)}")
            logger.warning(
                "commit_cash_movement_error",
                document_id=str(document_id),
                idx=idx,
                error=str(e),
            )

    # Commit all records
    await db.commit()

    # Recalculate positions for affected assets
    position_service = PositionService(db)
    positions_updated = 0

    for asset_id in asset_ids_to_recalculate:
        try:
            await position_service.calculate_position(
                account_id=request.account_id,
                asset_id=asset_id,
            )
            positions_updated += 1
        except Exception as e:
            errors.append(f"Position recalc for asset {asset_id}: {str(e)}")
            logger.error(
                "position_recalc_error",
                document_id=str(document_id),
                asset_id=str(asset_id),
                error=str(e),
            )

    await db.commit()

    logger.info(
        "commit_document_complete",
        document_id=str(document_id),
        transactions_created=transactions_created,
        assets_created=assets_created,
        fixed_income_created=fixed_income_created,
        cash_flows_created=cash_flows_created,
        positions_updated=positions_updated,
        errors_count=len(errors),
    )

    return CommitDocumentResponse(
        document_id=document_id,
        transactions_created=transactions_created,
        assets_created=assets_created,
        positions_updated=positions_updated,
        fixed_income_created=fixed_income_created,
        cash_flows_created=cash_flows_created,
        errors=errors,
    )


async def _get_or_create_asset(
    db: DBSession,
    ticker: str,
    asset_name: str | None,
    asset_type_str: str | None,
) -> tuple[Asset, bool]:
    """Get existing asset by ticker or create a new one.

    Returns:
        tuple[Asset, bool]: The asset and whether it was created (True) or existed (False).
    """
    # Normalize ticker
    ticker = ticker.upper().strip()

    # Check if asset exists
    query = select(Asset).where(Asset.ticker == ticker)
    result = await db.execute(query)
    asset = result.scalar_one_or_none()

    if asset:
        return asset, False

    # Determine asset type
    asset_type = _infer_asset_type(ticker, asset_type_str)

    # Create new asset
    asset = Asset(
        ticker=ticker,
        name=asset_name or ticker,
        asset_type=asset_type,
    )
    db.add(asset)
    await db.flush()

    return asset, True


def _infer_asset_type(ticker: str, asset_type_str: str | None) -> AssetType:
    """Infer asset type from ticker pattern or explicit type string."""
    # If explicitly provided, try to match
    if asset_type_str:
        type_map = {
            "stock": AssetType.STOCK,
            "acao": AssetType.STOCK,
            "acoes": AssetType.STOCK,
            "fii": AssetType.FII,
            "fiagro": AssetType.FIAGRO,
            "etf": AssetType.ETF,
            "bdr": AssetType.BDR,
            "reit": AssetType.REIT,
            "bond": AssetType.BOND,
            "renda_fixa": AssetType.BOND,
            "fixed_income": AssetType.BOND,
            "crypto": AssetType.CRYPTO,
            "fund": AssetType.FUND,
            "fundo": AssetType.FUND,
            "option": AssetType.OPTION,
            "opcao": AssetType.OPTION,
            "future": AssetType.FUTURE,
            "futuro": AssetType.FUTURE,
        }
        normalized = asset_type_str.lower().strip().replace(" ", "_")
        if normalized in type_map:
            return type_map[normalized]

    # Infer from ticker pattern (Brazilian market conventions)
    ticker_upper = ticker.upper()

    # FIIs typically end in 11
    if ticker_upper.endswith("11"):
        return AssetType.FII

    # BDRs typically end in 34 or 35
    if ticker_upper.endswith("34") or ticker_upper.endswith("35"):
        return AssetType.BDR

    # ETFs typically end in 11 and have known prefixes
    etf_prefixes = ["BOVA", "IVVB", "HASH", "SMAL", "FIND", "GOLD", "PIBB"]
    for prefix in etf_prefixes:
        if ticker_upper.startswith(prefix):
            return AssetType.ETF

    # Stocks typically end in 3, 4, 5, 6 for common shares
    if len(ticker_upper) >= 5:
        last_char = ticker_upper[-1]
        if last_char in "3456":
            return AssetType.STOCK

    # Default to stock
    return AssetType.STOCK


def _map_transaction_type(type_str: str) -> TransactionType:
    """Map string transaction type to enum."""
    type_map = {
        "buy": TransactionType.BUY,
        "compra": TransactionType.BUY,
        "sell": TransactionType.SELL,
        "venda": TransactionType.SELL,
        "dividend": TransactionType.DIVIDEND,
        "dividendo": TransactionType.DIVIDEND,
        "jcp": TransactionType.JCP,
        "jscp": TransactionType.JCP,
        "income": TransactionType.INCOME,
        "rendimento": TransactionType.INCOME,
        "amortization": TransactionType.AMORTIZATION,
        "amortizacao": TransactionType.AMORTIZATION,
        "split": TransactionType.SPLIT,
        "desdobramento": TransactionType.SPLIT,
        "subscription": TransactionType.SUBSCRIPTION,
        "subscricao": TransactionType.SUBSCRIPTION,
        "transfer_in": TransactionType.TRANSFER_IN,
        "transferencia_entrada": TransactionType.TRANSFER_IN,
        "transfer_out": TransactionType.TRANSFER_OUT,
        "transferencia_saida": TransactionType.TRANSFER_OUT,
        "rental": TransactionType.RENTAL,
        "aluguel": TransactionType.RENTAL,
        "other": TransactionType.OTHER,
        "outro": TransactionType.OTHER,
    }

    normalized = type_str.lower().strip().replace(" ", "_")
    return type_map.get(normalized, TransactionType.OTHER)


def _map_fixed_income_type(type_str: str) -> FixedIncomeType:
    """Map string fixed income type to enum."""
    type_map = {
        "cdb": FixedIncomeType.CDB,
        "lca": FixedIncomeType.LCA,
        "lci": FixedIncomeType.LCI,
        "lft": FixedIncomeType.LFT,
        "ltn": FixedIncomeType.LFT,  # Treat LTN as similar to LFT
        "ntnb": FixedIncomeType.NTNB,
        "ntn-b": FixedIncomeType.NTNB,
        "ntnf": FixedIncomeType.NTNF,
        "ntn-f": FixedIncomeType.NTNF,
        "lf": FixedIncomeType.LF,
        "letra_financeira": FixedIncomeType.LF,
        "debenture": FixedIncomeType.DEBENTURE,
        "debentures": FixedIncomeType.DEBENTURE,
        "cri": FixedIncomeType.CRI,
        "cra": FixedIncomeType.CRA,
        "tesouro_selic": FixedIncomeType.LFT,
        "tesouro_ipca": FixedIncomeType.NTNB,
        "tesouro_prefixado": FixedIncomeType.NTNF,
    }

    normalized = type_str.lower().strip().replace(" ", "_").replace("-", "")
    return type_map.get(normalized, FixedIncomeType.OTHER)


def _map_indexer_type(indexer_str: str) -> IndexerType:
    """Map string indexer type to enum."""
    type_map = {
        "cdi": IndexerType.CDI,
        "di": IndexerType.CDI,
        "selic": IndexerType.SELIC,
        "ipca": IndexerType.IPCA,
        "igpm": IndexerType.IGPM,
        "igp-m": IndexerType.IGPM,
        "prefixado": IndexerType.PREFIXADO,
        "pre": IndexerType.PREFIXADO,
    }

    normalized = indexer_str.lower().strip().replace(" ", "_").replace("-", "")
    return type_map.get(normalized, IndexerType.OTHER)


def _map_cash_flow_type(type_str: str) -> CashFlowType:
    """Map string cash flow type to enum."""
    type_map = {
        "deposit": CashFlowType.DEPOSIT,
        "deposito": CashFlowType.DEPOSIT,
        "aporte": CashFlowType.DEPOSIT,
        "withdrawal": CashFlowType.WITHDRAWAL,
        "saque": CashFlowType.WITHDRAWAL,
        "resgate": CashFlowType.WITHDRAWAL,
        "dividend": CashFlowType.DIVIDEND,
        "dividendo": CashFlowType.DIVIDEND,
        "jcp": CashFlowType.JCP,
        "jscp": CashFlowType.JCP,
        "interest": CashFlowType.INTEREST,
        "juros": CashFlowType.INTEREST,
        "rendimento": CashFlowType.INTEREST,
        "fee": CashFlowType.FEE,
        "taxa": CashFlowType.FEE,
        "tarifa": CashFlowType.FEE,
        "tax": CashFlowType.TAX,
        "imposto": CashFlowType.TAX,
        "ir": CashFlowType.TAX,
        "iof": CashFlowType.TAX,
        "settlement": CashFlowType.SETTLEMENT,
        "liquidacao": CashFlowType.SETTLEMENT,
        "rental_income": CashFlowType.RENTAL_INCOME,
        "aluguel": CashFlowType.RENTAL_INCOME,
        "renda_aluguel": CashFlowType.RENTAL_INCOME,
    }

    normalized = type_str.lower().strip().replace(" ", "_")
    return type_map.get(normalized, CashFlowType.OTHER)
