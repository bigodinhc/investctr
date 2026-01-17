"""
Position calculation service.

Calculates and maintains portfolio positions based on transactions.
Uses weighted average price method for position tracking.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Asset, Position, Transaction
from app.schemas.enums import PositionType, TransactionType

logger = get_logger(__name__)


class PositionService:
    """Service for calculating and managing positions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_position(
        self,
        account_id: UUID,
        asset_id: UUID,
        position_type: PositionType = PositionType.LONG,
    ) -> Position:
        """
        Calculate position for a specific account/asset combination.

        Processes all transactions chronologically and calculates:
        - Total quantity held
        - Weighted average purchase price
        - Total cost basis

        Args:
            account_id: Account UUID
            asset_id: Asset UUID
            position_type: Type of position (long/short)

        Returns:
            Updated Position object
        """
        logger.info(
            "position_calculation_start",
            account_id=str(account_id),
            asset_id=str(asset_id),
        )

        # Get all transactions for this account/asset, ordered chronologically
        query = (
            select(Transaction)
            .where(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.asset_id == asset_id,
                )
            )
            .order_by(Transaction.executed_at.asc())
        )
        result = await self.db.execute(query)
        transactions = result.scalars().all()

        # Calculate position from transactions
        quantity = Decimal("0")
        total_cost = Decimal("0")
        first_buy_date = None

        for txn in transactions:
            if txn.type in (TransactionType.BUY, TransactionType.SUBSCRIPTION):
                # Add to position
                txn_cost = txn.quantity * txn.price + txn.fees
                total_cost += txn_cost
                quantity += txn.quantity
                if first_buy_date is None:
                    first_buy_date = txn.executed_at

            elif txn.type == TransactionType.SELL:
                # Reduce position (proportionally reduce cost basis)
                if quantity > 0:
                    # Calculate proportion being sold
                    avg_price = total_cost / quantity
                    sold_cost = txn.quantity * avg_price
                    total_cost -= sold_cost
                    quantity -= txn.quantity

                    # Prevent negative values due to rounding
                    if quantity < 0:
                        quantity = Decimal("0")
                    if total_cost < 0:
                        total_cost = Decimal("0")

            elif txn.type == TransactionType.SPLIT:
                # Stock split: multiply quantity, keep total cost
                if txn.quantity > 0:
                    quantity = quantity * txn.quantity

            elif txn.type == TransactionType.TRANSFER_IN:
                # Transfer in: add quantity at specified price
                txn_cost = txn.quantity * txn.price
                total_cost += txn_cost
                quantity += txn.quantity
                if first_buy_date is None:
                    first_buy_date = txn.executed_at

            elif txn.type == TransactionType.TRANSFER_OUT:
                # Transfer out: reduce quantity proportionally
                if quantity > 0:
                    avg_price = total_cost / quantity
                    sold_cost = txn.quantity * avg_price
                    total_cost -= sold_cost
                    quantity -= txn.quantity

            # DIVIDEND, INCOME, JCP, AMORTIZATION don't affect position quantity

        # Calculate average price
        avg_price = total_cost / quantity if quantity > 0 else Decimal("0")

        # Get or create position
        position = await self._get_or_create_position(
            account_id=account_id,
            asset_id=asset_id,
            position_type=position_type,
        )

        # Update position
        position.quantity = quantity
        position.avg_price = avg_price
        position.total_cost = total_cost
        position.opened_at = first_buy_date
        position.updated_at = datetime.utcnow()

        await self.db.flush()

        logger.info(
            "position_calculation_complete",
            account_id=str(account_id),
            asset_id=str(asset_id),
            quantity=str(quantity),
            avg_price=str(avg_price),
            total_cost=str(total_cost),
        )

        return position

    async def recalculate_account_positions(self, account_id: UUID) -> list[Position]:
        """
        Recalculate all positions for an account.

        Args:
            account_id: Account UUID

        Returns:
            List of updated Position objects
        """
        logger.info("recalculate_account_start", account_id=str(account_id))

        # Get all unique assets with transactions for this account
        query = (
            select(Transaction.asset_id)
            .where(Transaction.account_id == account_id)
            .distinct()
        )
        result = await self.db.execute(query)
        asset_ids = [row[0] for row in result.fetchall()]

        positions = []
        for asset_id in asset_ids:
            position = await self.calculate_position(account_id, asset_id)
            positions.append(position)

        await self.db.commit()

        logger.info(
            "recalculate_account_complete",
            account_id=str(account_id),
            positions_count=len(positions),
        )

        return positions

    async def get_positions_with_assets(
        self,
        account_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> list[Position]:
        """
        Get positions with loaded asset data.

        Args:
            account_id: Filter by specific account (optional)
            user_id: Filter by user (via account ownership)

        Returns:
            List of Position objects with asset relationship loaded
        """
        query = (
            select(Position)
            .options(selectinload(Position.asset))
            .where(Position.quantity > 0)  # Only positions with quantity
        )

        if account_id:
            query = query.where(Position.account_id == account_id)

        if user_id:
            from app.models import Account
            query = query.join(Position.account).where(Account.user_id == user_id)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_consolidated_positions(self, user_id: UUID) -> list[dict]:
        """
        Get positions consolidated across all accounts for same asset.

        Args:
            user_id: User UUID

        Returns:
            List of consolidated position dictionaries
        """
        from app.models import Account

        # Get all positions for user's accounts, grouped by asset
        query = (
            select(
                Position.asset_id,
                Asset.ticker,
                Asset.name.label("asset_name"),
                Asset.asset_type,
                func.sum(Position.quantity).label("total_quantity"),
                func.sum(Position.total_cost).label("total_cost"),
                func.count(Position.account_id).label("accounts_count"),
            )
            .join(Position.account)
            .join(Position.asset)
            .where(
                and_(
                    Account.user_id == user_id,
                    Position.quantity > 0,
                )
            )
            .group_by(
                Position.asset_id,
                Asset.ticker,
                Asset.name,
                Asset.asset_type,
            )
        )

        result = await self.db.execute(query)
        rows = result.fetchall()

        consolidated = []
        for row in rows:
            total_quantity = row.total_quantity or Decimal("0")
            total_cost = row.total_cost or Decimal("0")

            consolidated.append({
                "asset_id": row.asset_id,
                "ticker": row.ticker,
                "asset_name": row.asset_name,
                "asset_type": row.asset_type,
                "total_quantity": total_quantity,
                "weighted_avg_price": (
                    total_cost / total_quantity if total_quantity > 0 else Decimal("0")
                ),
                "total_cost": total_cost,
                "current_price": None,  # To be filled by market data
                "market_value": None,
                "unrealized_pnl": None,
                "unrealized_pnl_pct": None,
                "accounts_count": row.accounts_count,
            })

        return consolidated

    async def _get_or_create_position(
        self,
        account_id: UUID,
        asset_id: UUID,
        position_type: PositionType,
    ) -> Position:
        """Get existing position or create a new one."""
        query = select(Position).where(
            and_(
                Position.account_id == account_id,
                Position.asset_id == asset_id,
                Position.position_type == position_type,
            )
        )
        result = await self.db.execute(query)
        position = result.scalar_one_or_none()

        if position is None:
            position = Position(
                account_id=account_id,
                asset_id=asset_id,
                position_type=position_type,
                quantity=Decimal("0"),
                avg_price=Decimal("0"),
                total_cost=Decimal("0"),
            )
            self.db.add(position)
            await self.db.flush()

        return position


async def recalculate_positions_after_transaction(
    db: AsyncSession,
    account_id: UUID,
    asset_id: UUID,
) -> Position:
    """
    Utility function to recalculate positions after a transaction change.

    Args:
        db: Database session
        account_id: Account UUID
        asset_id: Asset UUID

    Returns:
        Updated Position object
    """
    service = PositionService(db)
    return await service.calculate_position(account_id, asset_id)
