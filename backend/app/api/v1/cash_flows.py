"""
Cash flow management endpoints (deposits and withdrawals).
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AuthenticatedUser, DBSession, Pagination
from app.models import Account, CashFlow
from app.schemas.cash_flow import (
    CashFlowCreate,
    CashFlowResponse,
    CashFlowsListResponse,
    CashFlowUpdate,
)

router = APIRouter(prefix="/cash-flows", tags=["cash-flows"])


async def verify_account_ownership(
    db: DBSession,
    account_id: UUID,
    user_id: UUID,
) -> Account:
    """Verify that the account belongs to the user."""
    query = (
        select(Account)
        .where(Account.id == account_id)
        .where(Account.user_id == user_id)
        .where(Account.is_active == True)
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or does not belong to user",
        )
    return account


@router.get("", response_model=CashFlowsListResponse)
async def list_cash_flows(
    user: AuthenticatedUser,
    db: DBSession,
    pagination: Pagination,
    account_id: UUID | None = Query(None, description="Filter by account ID"),
) -> CashFlowsListResponse:
    """List all cash flows for the authenticated user."""
    # Build base query - join with accounts to filter by user
    base_query = (
        select(CashFlow)
        .join(Account, CashFlow.account_id == Account.id)
        .where(Account.user_id == user.id)
        .where(Account.is_active == True)
    )

    # Apply account filter if provided
    if account_id:
        base_query = base_query.where(CashFlow.account_id == account_id)

    # Query with pagination
    query = (
        base_query.offset(pagination.skip)
        .limit(pagination.limit)
        .order_by(CashFlow.executed_at.desc())
    )
    result = await db.execute(query)
    cash_flows = result.scalars().all()

    # Get total count
    count_result = await db.execute(base_query)
    total = len(count_result.scalars().all())

    return CashFlowsListResponse(
        items=[CashFlowResponse.model_validate(cf) for cf in cash_flows],
        total=total,
    )


@router.post("", response_model=CashFlowResponse, status_code=status.HTTP_201_CREATED)
async def create_cash_flow(
    user: AuthenticatedUser,
    db: DBSession,
    cash_flow_in: CashFlowCreate,
) -> CashFlowResponse:
    """Create a new cash flow (deposit or withdrawal)."""
    # Verify account ownership
    await verify_account_ownership(db, cash_flow_in.account_id, user.id)

    cash_flow = CashFlow(
        account_id=cash_flow_in.account_id,
        type=cash_flow_in.type,
        amount=cash_flow_in.amount,
        currency=cash_flow_in.currency.value,
        exchange_rate=cash_flow_in.exchange_rate,
        executed_at=cash_flow_in.executed_at,
        shares_affected=cash_flow_in.shares_affected,
        notes=cash_flow_in.notes,
    )

    try:
        db.add(cash_flow)
        await db.commit()
        await db.refresh(cash_flow)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create cash flow due to constraint violation",
        ) from e

    return CashFlowResponse.model_validate(cash_flow)


@router.get("/{cash_flow_id}", response_model=CashFlowResponse)
async def get_cash_flow(
    user: AuthenticatedUser,
    db: DBSession,
    cash_flow_id: UUID,
) -> CashFlowResponse:
    """Get a specific cash flow by ID."""
    query = (
        select(CashFlow)
        .join(Account, CashFlow.account_id == Account.id)
        .where(CashFlow.id == cash_flow_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    cash_flow = result.scalar_one_or_none()

    if not cash_flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash flow not found",
        )

    return CashFlowResponse.model_validate(cash_flow)


@router.put("/{cash_flow_id}", response_model=CashFlowResponse)
async def update_cash_flow(
    user: AuthenticatedUser,
    db: DBSession,
    cash_flow_id: UUID,
    cash_flow_in: CashFlowUpdate,
) -> CashFlowResponse:
    """Update an existing cash flow."""
    query = (
        select(CashFlow)
        .join(Account, CashFlow.account_id == Account.id)
        .where(CashFlow.id == cash_flow_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    cash_flow = result.scalar_one_or_none()

    if not cash_flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash flow not found",
        )

    # Update fields if provided
    update_data = cash_flow_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Handle enum fields
        if field == "type" and value is not None:
            setattr(cash_flow, field, value)
        elif field == "currency" and value is not None:
            setattr(cash_flow, field, value.value if hasattr(value, "value") else value)
        else:
            setattr(cash_flow, field, value)

    try:
        await db.commit()
        await db.refresh(cash_flow)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to constraint violation",
        ) from e

    return CashFlowResponse.model_validate(cash_flow)


@router.delete("/{cash_flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cash_flow(
    user: AuthenticatedUser,
    db: DBSession,
    cash_flow_id: UUID,
) -> None:
    """Delete a cash flow."""
    query = (
        select(CashFlow)
        .join(Account, CashFlow.account_id == Account.id)
        .where(CashFlow.id == cash_flow_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    cash_flow = result.scalar_one_or_none()

    if not cash_flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cash flow not found",
        )

    await db.delete(cash_flow)
    await db.commit()
