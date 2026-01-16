"""
Account management endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AuthenticatedUser, DBSession, Pagination
from app.models import Account
from app.schemas.account import (
    AccountCreate,
    AccountResponse,
    AccountsListResponse,
    AccountUpdate,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=AccountsListResponse)
async def list_accounts(
    user: AuthenticatedUser,
    db: DBSession,
    pagination: Pagination,
) -> AccountsListResponse:
    """List all accounts for the authenticated user."""
    # Query accounts for this user
    query = (
        select(Account)
        .where(Account.user_id == user.id)
        .where(Account.is_active == True)
        .offset(pagination.skip)
        .limit(pagination.limit)
        .order_by(Account.created_at.desc())
    )
    result = await db.execute(query)
    accounts = result.scalars().all()

    # Get total count
    count_query = (
        select(Account)
        .where(Account.user_id == user.id)
        .where(Account.is_active == True)
    )
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return AccountsListResponse(
        items=[AccountResponse.model_validate(acc) for acc in accounts],
        total=total,
    )


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    user: AuthenticatedUser,
    db: DBSession,
    account_in: AccountCreate,
) -> AccountResponse:
    """Create a new account."""
    account = Account(
        user_id=user.id,
        name=account_in.name,
        type=account_in.type,
        currency=account_in.currency.value,
    )

    try:
        db.add(account)
        await db.commit()
        await db.refresh(account)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account with this name already exists",
        ) from e

    return AccountResponse.model_validate(account)


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    user: AuthenticatedUser,
    db: DBSession,
    account_id: UUID,
) -> AccountResponse:
    """Get a specific account by ID."""
    query = (
        select(Account)
        .where(Account.id == account_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return AccountResponse.model_validate(account)


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    user: AuthenticatedUser,
    db: DBSession,
    account_id: UUID,
    account_in: AccountUpdate,
) -> AccountResponse:
    """Update an existing account."""
    query = (
        select(Account)
        .where(Account.id == account_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    # Update fields if provided
    update_data = account_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    try:
        await db.commit()
        await db.refresh(account)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to constraint violation",
        ) from e

    return AccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    user: AuthenticatedUser,
    db: DBSession,
    account_id: UUID,
) -> None:
    """Delete an account (soft delete by setting is_active=False)."""
    query = (
        select(Account)
        .where(Account.id == account_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    # Soft delete
    account.is_active = False
    await db.commit()
