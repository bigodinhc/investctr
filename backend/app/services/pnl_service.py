"""
P&L (Profit and Loss) calculation service.

Calculates realized and unrealized P&L based on transactions.
Uses weighted average price method consistent with position tracking.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Account, Asset, Position, Transaction
from app.schemas.enums import TransactionType

logger = get_logger(__name__)


@dataclass
class RealizedPnLEntry:
    """Single realized P&L entry from a sale transaction."""

    transaction_id: UUID
    asset_id: UUID
    ticker: str | None
    executed_at: datetime
    quantity_sold: Decimal
    sale_price: Decimal
    avg_cost_price: Decimal
    sale_proceeds: Decimal  # quantity * sale_price - fees
    cost_basis: Decimal  # quantity * avg_cost_price
    realized_pnl: Decimal  # sale_proceeds - cost_basis
    fees: Decimal


@dataclass
class RealizedPnLSummary:
    """Summary of realized P&L for a period or account."""

    total_realized_pnl: Decimal
    total_sales_proceeds: Decimal
    total_cost_basis: Decimal
    total_fees: Decimal
    transaction_count: int
    entries: list[RealizedPnLEntry]


class PnLService:
    """Service for calculating P&L (Profit and Loss)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_realized_pnl(
        self,
        account_id: UUID | None = None,
        asset_id: UUID | None = None,
        user_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> RealizedPnLSummary:
        """
        Calculate realized P&L from sale transactions.

        Uses weighted average price method:
        - Tracks running average cost as buys are made
        - When sold, P&L = (sale_price - avg_cost) * quantity - fees

        Args:
            account_id: Filter by specific account (optional)
            asset_id: Filter by specific asset (optional)
            user_id: Filter by user's accounts (optional)
            start_date: Start date filter for transactions (optional)
            end_date: End date filter for transactions (optional)

        Returns:
            RealizedPnLSummary with all realized P&L entries
        """
        logger.info(
            "calculate_realized_pnl_start",
            account_id=str(account_id) if account_id else None,
            asset_id=str(asset_id) if asset_id else None,
            user_id=str(user_id) if user_id else None,
        )

        # Build query for transactions
        query = (
            select(Transaction)
            .options(selectinload(Transaction.asset))
            .order_by(Transaction.asset_id, Transaction.executed_at.asc())
        )

        # Apply filters
        if account_id:
            query = query.where(Transaction.account_id == account_id)

        if asset_id:
            query = query.where(Transaction.asset_id == asset_id)

        if user_id:
            query = query.join(Transaction.account).where(Account.user_id == user_id)

        if start_date:
            query = query.where(Transaction.executed_at >= datetime.combine(start_date, datetime.min.time()))

        if end_date:
            query = query.where(Transaction.executed_at <= datetime.combine(end_date, datetime.max.time()))

        result = await self.db.execute(query)
        transactions = list(result.scalars().all())

        # Group transactions by asset to calculate P&L per asset
        entries: list[RealizedPnLEntry] = []
        asset_states: dict[UUID, dict] = {}  # Track running avg cost per asset

        for txn in transactions:
            aid = txn.asset_id

            # Initialize asset state if first transaction
            if aid not in asset_states:
                asset_states[aid] = {
                    "quantity": Decimal("0"),
                    "total_cost": Decimal("0"),
                }

            state = asset_states[aid]

            if txn.type in (TransactionType.BUY, TransactionType.SUBSCRIPTION):
                # Add to position with cost including fees
                txn_cost = txn.quantity * txn.price + txn.fees
                state["total_cost"] += txn_cost
                state["quantity"] += txn.quantity

            elif txn.type == TransactionType.SELL:
                # Calculate realized P&L using weighted average cost
                if state["quantity"] > 0:
                    avg_cost = state["total_cost"] / state["quantity"]
                else:
                    avg_cost = Decimal("0")

                sale_quantity = txn.quantity
                sale_price = txn.price
                fees = txn.fees

                # Calculate P&L
                sale_proceeds = sale_quantity * sale_price - fees
                cost_basis = sale_quantity * avg_cost
                realized_pnl = sale_proceeds - cost_basis

                entry = RealizedPnLEntry(
                    transaction_id=txn.id,
                    asset_id=aid,
                    ticker=txn.asset.ticker if txn.asset else None,
                    executed_at=txn.executed_at,
                    quantity_sold=sale_quantity,
                    sale_price=sale_price,
                    avg_cost_price=avg_cost,
                    sale_proceeds=sale_proceeds,
                    cost_basis=cost_basis,
                    realized_pnl=realized_pnl,
                    fees=fees,
                )
                entries.append(entry)

                # Update running state (reduce position)
                cost_reduction = sale_quantity * avg_cost
                state["total_cost"] -= cost_reduction
                state["quantity"] -= sale_quantity

                # Prevent negative from rounding
                if state["quantity"] < 0:
                    state["quantity"] = Decimal("0")
                if state["total_cost"] < 0:
                    state["total_cost"] = Decimal("0")

            elif txn.type == TransactionType.TRANSFER_IN:
                # Add to position at given price
                txn_cost = txn.quantity * txn.price
                state["total_cost"] += txn_cost
                state["quantity"] += txn.quantity

            elif txn.type == TransactionType.TRANSFER_OUT:
                # Reduce position (similar to sell but no P&L)
                if state["quantity"] > 0:
                    avg_cost = state["total_cost"] / state["quantity"]
                    cost_reduction = txn.quantity * avg_cost
                    state["total_cost"] -= cost_reduction
                    state["quantity"] -= txn.quantity

                    if state["quantity"] < 0:
                        state["quantity"] = Decimal("0")
                    if state["total_cost"] < 0:
                        state["total_cost"] = Decimal("0")

            elif txn.type == TransactionType.SPLIT:
                # Stock split: multiply quantity, keep total cost
                if txn.quantity > 0:
                    state["quantity"] = state["quantity"] * txn.quantity

        # Calculate totals
        total_pnl = sum(e.realized_pnl for e in entries)
        total_proceeds = sum(e.sale_proceeds for e in entries)
        total_cost = sum(e.cost_basis for e in entries)
        total_fees = sum(e.fees for e in entries)

        summary = RealizedPnLSummary(
            total_realized_pnl=total_pnl,
            total_sales_proceeds=total_proceeds,
            total_cost_basis=total_cost,
            total_fees=total_fees,
            transaction_count=len(entries),
            entries=entries,
        )

        logger.info(
            "calculate_realized_pnl_complete",
            transaction_count=len(entries),
            total_realized_pnl=str(total_pnl),
        )

        return summary

    async def calculate_realized_pnl_by_asset(
        self,
        account_id: UUID | None = None,
        user_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[UUID, RealizedPnLSummary]:
        """
        Calculate realized P&L grouped by asset.

        Args:
            account_id: Filter by specific account (optional)
            user_id: Filter by user's accounts (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            Dictionary mapping asset_id -> RealizedPnLSummary
        """
        # Get overall summary with all entries
        summary = await self.calculate_realized_pnl(
            account_id=account_id,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Group entries by asset
        by_asset: dict[UUID, list[RealizedPnLEntry]] = {}
        for entry in summary.entries:
            if entry.asset_id not in by_asset:
                by_asset[entry.asset_id] = []
            by_asset[entry.asset_id].append(entry)

        # Create summary per asset
        result: dict[UUID, RealizedPnLSummary] = {}
        for aid, entries in by_asset.items():
            result[aid] = RealizedPnLSummary(
                total_realized_pnl=sum(e.realized_pnl for e in entries),
                total_sales_proceeds=sum(e.sale_proceeds for e in entries),
                total_cost_basis=sum(e.cost_basis for e in entries),
                total_fees=sum(e.fees for e in entries),
                transaction_count=len(entries),
                entries=entries,
            )

        return result

    async def get_unrealized_pnl(
        self,
        positions: list[Position],
        current_prices: dict[UUID, Decimal],
    ) -> dict[UUID, dict]:
        """
        Calculate unrealized P&L for open positions.

        Args:
            positions: List of Position objects
            current_prices: Dictionary mapping asset_id -> current price

        Returns:
            Dictionary mapping position_id -> unrealized P&L info
        """
        result: dict[UUID, dict] = {}

        for pos in positions:
            if pos.quantity <= 0:
                continue

            current_price = current_prices.get(pos.asset_id)
            if current_price is None:
                result[pos.id] = {
                    "position_id": pos.id,
                    "asset_id": pos.asset_id,
                    "quantity": pos.quantity,
                    "avg_price": pos.avg_price,
                    "total_cost": pos.total_cost,
                    "current_price": None,
                    "market_value": None,
                    "unrealized_pnl": None,
                    "unrealized_pnl_pct": None,
                }
                continue

            market_value = pos.quantity * current_price
            unrealized_pnl = market_value - pos.total_cost
            unrealized_pnl_pct = (
                (unrealized_pnl / pos.total_cost * 100)
                if pos.total_cost > 0
                else Decimal("0")
            )

            result[pos.id] = {
                "position_id": pos.id,
                "asset_id": pos.asset_id,
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "total_cost": pos.total_cost,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
            }

        return result


async def calculate_realized_pnl(
    db: AsyncSession,
    account_id: UUID | None = None,
    asset_id: UUID | None = None,
    user_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> RealizedPnLSummary:
    """
    Utility function to calculate realized P&L.

    Args:
        db: Database session
        account_id: Filter by account (optional)
        asset_id: Filter by asset (optional)
        user_id: Filter by user (optional)
        start_date: Start date filter (optional)
        end_date: End date filter (optional)

    Returns:
        RealizedPnLSummary with P&L details
    """
    service = PnLService(db)
    return await service.calculate_realized_pnl(
        account_id=account_id,
        asset_id=asset_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
