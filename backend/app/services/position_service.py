"""
Position calculation service.

Calculates and maintains portfolio positions based on transactions.
Uses weighted average price method for position tracking.
Implements netting model: one position per asset (LONG or SHORT, never both).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Asset, Position, Transaction
from app.schemas.enums import PositionType, TransactionType

logger = get_logger(__name__)


@dataclass
class PositionState:
    """Tracks the current state of a position during calculation."""

    position_type: PositionType | None  # None = no position
    quantity: Decimal
    total_cost: Decimal
    avg_price: Decimal
    first_date: datetime | None

    @classmethod
    def empty(cls) -> "PositionState":
        """Create an empty position state."""
        return cls(
            position_type=None,
            quantity=Decimal("0"),
            total_cost=Decimal("0"),
            avg_price=Decimal("0"),
            first_date=None,
        )

    def add_long(
        self, quantity: Decimal, price: Decimal, fees: Decimal, executed_at: datetime
    ) -> None:
        """Add to LONG position (BUY)."""
        txn_cost = quantity * price + fees

        if self.position_type == PositionType.SHORT:
            # Closing SHORT position (BUY to cover)
            if quantity <= self.quantity:
                # Partial or full close of SHORT
                self.quantity -= quantity
                # Cost basis reduced proportionally
                cost_per_unit = (
                    self.total_cost / (self.quantity + quantity)
                    if (self.quantity + quantity) > 0
                    else Decimal("0")
                )
                self.total_cost -= quantity * cost_per_unit

                if self.quantity == Decimal("0"):
                    # SHORT fully closed
                    self.position_type = None
                    self.total_cost = Decimal("0")
                    self.avg_price = Decimal("0")
                else:
                    self.avg_price = (
                        self.total_cost / self.quantity
                        if self.quantity > 0
                        else Decimal("0")
                    )
            else:
                # Close SHORT and flip to LONG
                excess = quantity - self.quantity
                self.position_type = PositionType.LONG
                self.quantity = excess
                self.total_cost = excess * price + (
                    fees * excess / quantity
                )  # Proportional fees
                self.avg_price = (
                    self.total_cost / self.quantity
                    if self.quantity > 0
                    else Decimal("0")
                )
                self.first_date = executed_at
        else:
            # Adding to LONG position or opening new LONG
            self.total_cost += txn_cost
            self.quantity += quantity
            self.position_type = PositionType.LONG
            self.avg_price = (
                self.total_cost / self.quantity if self.quantity > 0 else Decimal("0")
            )
            if self.first_date is None:
                self.first_date = executed_at

    def reduce_long(
        self, quantity: Decimal, price: Decimal, fees: Decimal, executed_at: datetime
    ) -> None:
        """Reduce LONG position (SELL) or open/increase SHORT."""
        if self.position_type == PositionType.LONG:
            if quantity <= self.quantity:
                # Partial or full close of LONG
                avg_cost = (
                    self.total_cost / self.quantity
                    if self.quantity > 0
                    else Decimal("0")
                )
                sold_cost = quantity * avg_cost
                self.total_cost -= sold_cost
                self.quantity -= quantity

                if self.quantity == Decimal("0"):
                    # LONG fully closed
                    self.position_type = None
                    self.total_cost = Decimal("0")
                    self.avg_price = Decimal("0")
                else:
                    self.avg_price = (
                        self.total_cost / self.quantity
                        if self.quantity > 0
                        else Decimal("0")
                    )
            else:
                # Close LONG and flip to SHORT
                excess = quantity - self.quantity
                self.position_type = PositionType.SHORT
                self.quantity = excess
                # SHORT cost basis = sale price (the price at which we opened the SHORT)
                self.total_cost = excess * price
                self.avg_price = price  # SHORT avg price = price we sold at
                self.first_date = executed_at
        elif self.position_type == PositionType.SHORT:
            # Adding to SHORT position (selling more)
            # Recalculate weighted average SHORT price
            new_cost = quantity * price
            self.total_cost += new_cost
            self.quantity += quantity
            self.avg_price = (
                self.total_cost / self.quantity if self.quantity > 0 else Decimal("0")
            )
        else:
            # Opening new SHORT position
            self.position_type = PositionType.SHORT
            self.quantity = quantity
            self.total_cost = quantity * price
            self.avg_price = price
            self.first_date = executed_at

    def apply_split(self, factor: Decimal) -> None:
        """Apply stock split. Multiply quantity, keep total cost."""
        if factor > 0 and self.quantity > 0:
            self.quantity = self.quantity * factor
            self.avg_price = (
                self.total_cost / self.quantity if self.quantity > 0 else Decimal("0")
            )

    def transfer_in(
        self, quantity: Decimal, price: Decimal, executed_at: datetime
    ) -> None:
        """Handle transfer in. Adds to LONG position."""
        self.add_long(quantity, price, Decimal("0"), executed_at)

    def transfer_out(self, quantity: Decimal) -> None:
        """Handle transfer out. Reduces LONG position without P&L."""
        if self.position_type == PositionType.LONG and self.quantity > 0:
            avg_cost = self.total_cost / self.quantity
            if quantity <= self.quantity:
                self.total_cost -= quantity * avg_cost
                self.quantity -= quantity
                if self.quantity <= Decimal("0"):
                    self.position_type = None
                    self.quantity = Decimal("0")
                    self.total_cost = Decimal("0")
                    self.avg_price = Decimal("0")
                else:
                    self.avg_price = self.total_cost / self.quantity


class PositionService:
    """Service for calculating and managing positions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_position(
        self,
        account_id: UUID,
        asset_id: UUID,
        position_type: PositionType = PositionType.LONG,  # Deprecated, determined dynamically
    ) -> Position | None:
        """
        Calculate position for a specific account/asset combination.

        Implements NETTING model:
        - Only ONE position per asset (LONG or SHORT, never both simultaneously)
        - SELL with no LONG position → opens SHORT
        - BUY with SHORT position → closes SHORT first, excess opens LONG

        Processes all transactions chronologically and calculates:
        - Position type (LONG or SHORT)
        - Total quantity held
        - Weighted average price
        - Total cost basis

        Args:
            account_id: Account UUID
            asset_id: Asset UUID
            position_type: DEPRECATED - position type is now determined dynamically

        Returns:
            Updated Position object, or None if no position
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

        # Calculate position using netting model
        state = PositionState.empty()

        for txn in transactions:
            if txn.type in (TransactionType.BUY, TransactionType.SUBSCRIPTION):
                # BUY: adds to LONG or closes SHORT
                state.add_long(txn.quantity, txn.price, txn.fees, txn.executed_at)

            elif txn.type == TransactionType.SELL:
                # SELL: reduces LONG or opens/increases SHORT
                state.reduce_long(txn.quantity, txn.price, txn.fees, txn.executed_at)

            elif txn.type == TransactionType.SPLIT:
                # Stock split: multiply quantity, keep total cost
                state.apply_split(txn.quantity)

            elif txn.type == TransactionType.TRANSFER_IN:
                # Transfer in: add quantity at specified price (like BUY)
                state.transfer_in(txn.quantity, txn.price, txn.executed_at)

            elif txn.type == TransactionType.TRANSFER_OUT:
                # Transfer out: reduce quantity (like SELL but no P&L)
                state.transfer_out(txn.quantity)

            # DIVIDEND, INCOME, JCP, AMORTIZATION don't affect position quantity

        # Delete any existing positions for this account/asset (clean slate)
        await self._delete_all_positions(account_id, asset_id)

        # Create new position if there's quantity
        if state.quantity > Decimal("0") and state.position_type is not None:
            position = Position(
                account_id=account_id,
                asset_id=asset_id,
                position_type=state.position_type,
                quantity=state.quantity,
                avg_price=state.avg_price,
                total_cost=state.total_cost,
                opened_at=state.first_date,
                updated_at=datetime.utcnow(),
            )
            self.db.add(position)
            await self.db.flush()

            logger.info(
                "position_calculation_complete",
                account_id=str(account_id),
                asset_id=str(asset_id),
                position_type=state.position_type.value,
                quantity=str(state.quantity),
                avg_price=str(state.avg_price),
                total_cost=str(state.total_cost),
            )

            return position
        else:
            logger.info(
                "position_calculation_complete_no_position",
                account_id=str(account_id),
                asset_id=str(asset_id),
            )
            return None

    async def _delete_all_positions(self, account_id: UUID, asset_id: UUID) -> None:
        """Delete all positions for an account/asset (LONG and SHORT)."""
        stmt = delete(Position).where(
            and_(
                Position.account_id == account_id,
                Position.asset_id == asset_id,
            )
        )
        await self.db.execute(stmt)

    async def recalculate_account_positions(self, account_id: UUID) -> list[Position]:
        """
        Recalculate all positions for an account.

        Args:
            account_id: Account UUID

        Returns:
            List of updated Position objects (excludes None for closed positions)
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
            if position is not None:
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

            consolidated.append(
                {
                    "asset_id": row.asset_id,
                    "ticker": row.ticker,
                    "asset_name": row.asset_name,
                    "asset_type": row.asset_type,
                    "total_quantity": total_quantity,
                    "weighted_avg_price": (
                        total_cost / total_quantity
                        if total_quantity > 0
                        else Decimal("0")
                    ),
                    "total_cost": total_cost,
                    "current_price": None,  # To be filled by market data
                    "market_value": None,
                    "unrealized_pnl": None,
                    "unrealized_pnl_pct": None,
                    "accounts_count": row.accounts_count,
                }
            )

        return consolidated


async def recalculate_positions_after_transaction(
    db: AsyncSession,
    account_id: UUID,
    asset_id: UUID,
) -> Position | None:
    """
    Utility function to recalculate positions after a transaction change.

    Args:
        db: Database session
        account_id: Account UUID
        asset_id: Asset UUID

    Returns:
        Updated Position object, or None if no position
    """
    service = PositionService(db)
    return await service.calculate_position(account_id, asset_id)
