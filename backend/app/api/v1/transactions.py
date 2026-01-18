"""
Transaction management endpoints.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import AuthenticatedUser, DBSession, Pagination
from app.core.logging import get_logger
from app.models import Account, Asset, Transaction
from app.schemas.enums import TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionsWithAssetListResponse,
    TransactionUpdate,
    TransactionWithAsset,
)
from app.services.position_service import recalculate_positions_after_transaction

logger = get_logger(__name__)
router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionsWithAssetListResponse)
async def list_transactions(
    user: AuthenticatedUser,
    db: DBSession,
    pagination: Pagination,
    account_id: UUID | None = Query(None, description="Filter by account"),
    asset_id: UUID | None = Query(None, description="Filter by asset"),
    type_filter: TransactionType | None = Query(None, description="Filter by type"),
    start_date: datetime | None = Query(None, description="Filter from date"),
    end_date: datetime | None = Query(None, description="Filter to date"),
) -> TransactionsWithAssetListResponse:
    """
    List all transactions for the authenticated user.

    Supports filtering by account, asset, type, and date range.
    Returns transactions with associated asset information.
    """
    # Base query with joins for user validation and asset data
    query = (
        select(Transaction)
        .join(Transaction.account)
        .join(Transaction.asset)
        .options(selectinload(Transaction.asset))
        .where(Account.user_id == user.id)
        .offset(pagination.skip)
        .limit(pagination.limit)
        .order_by(Transaction.executed_at.desc())
    )

    # Apply filters
    if account_id:
        query = query.where(Transaction.account_id == account_id)
    if asset_id:
        query = query.where(Transaction.asset_id == asset_id)
    if type_filter:
        query = query.where(Transaction.type == type_filter)
    if start_date:
        query = query.where(Transaction.executed_at >= start_date)
    if end_date:
        query = query.where(Transaction.executed_at <= end_date)

    result = await db.execute(query)
    transactions = result.scalars().all()

    # Get total count with same filters
    count_query = (
        select(func.count(Transaction.id))
        .join(Transaction.account)
        .where(Account.user_id == user.id)
    )
    if account_id:
        count_query = count_query.where(Transaction.account_id == account_id)
    if asset_id:
        count_query = count_query.where(Transaction.asset_id == asset_id)
    if type_filter:
        count_query = count_query.where(Transaction.type == type_filter)
    if start_date:
        count_query = count_query.where(Transaction.executed_at >= start_date)
    if end_date:
        count_query = count_query.where(Transaction.executed_at <= end_date)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Convert to response with asset info
    items = []
    for txn in transactions:
        item = TransactionWithAsset(
            id=txn.id,
            account_id=txn.account_id,
            asset_id=txn.asset_id,
            document_id=txn.document_id,
            type=txn.type,
            quantity=txn.quantity,
            price=txn.price,
            total_value=txn.quantity * txn.price,
            fees=txn.fees,
            currency=txn.currency,
            exchange_rate=txn.exchange_rate,
            executed_at=txn.executed_at,
            notes=txn.notes,
            created_at=txn.created_at,
            ticker=txn.asset.ticker,
            asset_name=txn.asset.name,
        )
        items.append(item)

    return TransactionsWithAssetListResponse(items=items, total=total)


@router.post(
    "", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
async def create_transaction(
    user: AuthenticatedUser,
    db: DBSession,
    transaction_in: TransactionCreate,
) -> TransactionResponse:
    """
    Create a new transaction manually.

    This will also trigger position recalculation for the affected asset.
    """
    # Validate account belongs to user
    account_query = (
        select(Account)
        .where(Account.id == transaction_in.account_id)
        .where(Account.user_id == user.id)
    )
    account_result = await db.execute(account_query)
    account = account_result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account not found or doesn't belong to user",
        )

    # Validate asset exists
    asset_query = select(Asset).where(Asset.id == transaction_in.asset_id)
    asset_result = await db.execute(asset_query)
    asset = asset_result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset not found",
        )

    # Create transaction
    transaction = Transaction(
        account_id=transaction_in.account_id,
        asset_id=transaction_in.asset_id,
        document_id=transaction_in.document_id,
        type=transaction_in.type,
        quantity=transaction_in.quantity,
        price=transaction_in.price,
        fees=transaction_in.fees,
        currency=transaction_in.currency.value,
        exchange_rate=transaction_in.exchange_rate,
        executed_at=transaction_in.executed_at,
        notes=transaction_in.notes,
    )

    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    # Recalculate position
    try:
        await recalculate_positions_after_transaction(
            db=db,
            account_id=transaction_in.account_id,
            asset_id=transaction_in.asset_id,
        )
        await db.commit()
    except Exception as e:
        logger.error(
            "position_recalc_error_on_create",
            transaction_id=str(transaction.id),
            error=str(e),
        )

    return TransactionResponse(
        id=transaction.id,
        account_id=transaction.account_id,
        asset_id=transaction.asset_id,
        document_id=transaction.document_id,
        type=transaction.type,
        quantity=transaction.quantity,
        price=transaction.price,
        total_value=transaction.quantity * transaction.price,
        fees=transaction.fees,
        currency=transaction.currency,
        exchange_rate=transaction.exchange_rate,
        executed_at=transaction.executed_at,
        notes=transaction.notes,
        created_at=transaction.created_at,
    )


@router.get("/{transaction_id}", response_model=TransactionWithAsset)
async def get_transaction(
    user: AuthenticatedUser,
    db: DBSession,
    transaction_id: UUID,
) -> TransactionWithAsset:
    """Get a specific transaction by ID."""
    query = (
        select(Transaction)
        .join(Transaction.account)
        .options(selectinload(Transaction.asset))
        .where(Transaction.id == transaction_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return TransactionWithAsset(
        id=transaction.id,
        account_id=transaction.account_id,
        asset_id=transaction.asset_id,
        document_id=transaction.document_id,
        type=transaction.type,
        quantity=transaction.quantity,
        price=transaction.price,
        total_value=transaction.quantity * transaction.price,
        fees=transaction.fees,
        currency=transaction.currency,
        exchange_rate=transaction.exchange_rate,
        executed_at=transaction.executed_at,
        notes=transaction.notes,
        created_at=transaction.created_at,
        ticker=transaction.asset.ticker,
        asset_name=transaction.asset.name,
    )


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    user: AuthenticatedUser,
    db: DBSession,
    transaction_id: UUID,
    transaction_in: TransactionUpdate,
) -> TransactionResponse:
    """
    Update an existing transaction.

    This will trigger position recalculation for the affected asset.
    """
    # Get transaction with user validation
    query = (
        select(Transaction)
        .join(Transaction.account)
        .where(Transaction.id == transaction_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Store original values for position recalc
    original_account_id = transaction.account_id
    original_asset_id = transaction.asset_id

    # Update fields if provided
    update_data = transaction_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)

    await db.commit()
    await db.refresh(transaction)

    # Recalculate position
    try:
        await recalculate_positions_after_transaction(
            db=db,
            account_id=original_account_id,
            asset_id=original_asset_id,
        )
        await db.commit()
    except Exception as e:
        logger.error(
            "position_recalc_error_on_update",
            transaction_id=str(transaction.id),
            error=str(e),
        )

    return TransactionResponse(
        id=transaction.id,
        account_id=transaction.account_id,
        asset_id=transaction.asset_id,
        document_id=transaction.document_id,
        type=transaction.type,
        quantity=transaction.quantity,
        price=transaction.price,
        total_value=transaction.quantity * transaction.price,
        fees=transaction.fees,
        currency=transaction.currency,
        exchange_rate=transaction.exchange_rate,
        executed_at=transaction.executed_at,
        notes=transaction.notes,
        created_at=transaction.created_at,
    )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    user: AuthenticatedUser,
    db: DBSession,
    transaction_id: UUID,
) -> None:
    """
    Delete a transaction.

    This will trigger position recalculation for the affected asset.
    """
    # Get transaction with user validation
    query = (
        select(Transaction)
        .join(Transaction.account)
        .where(Transaction.id == transaction_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Store values for position recalc
    account_id = transaction.account_id
    asset_id = transaction.asset_id

    await db.delete(transaction)
    await db.commit()

    # Recalculate position
    try:
        await recalculate_positions_after_transaction(
            db=db,
            account_id=account_id,
            asset_id=asset_id,
        )
        await db.commit()
    except Exception as e:
        logger.error(
            "position_recalc_error_on_delete",
            transaction_id=str(transaction_id),
            error=str(e),
        )
