"""
P&L (Profit and Loss) calculation service.

Calculates realized and unrealized P&L based on transactions.
Uses weighted average price method consistent with position tracking.
Implements netting model: LONG/SHORT positions with proper P&L for both.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Account, Position, Transaction
from app.schemas.enums import TransactionType

logger = get_logger(__name__)


class PnLType(str, Enum):
    """Type of realized P&L event."""

    LONG_CLOSE = "long_close"  # Closing LONG position (SELL)
    SHORT_CLOSE = "short_close"  # Closing SHORT position (BUY)


@dataclass
class RealizedPnLEntry:
    """Single realized P&L entry from closing a position (LONG or SHORT)."""

    transaction_id: UUID
    asset_id: UUID
    ticker: str | None
    executed_at: datetime
    pnl_type: PnLType  # LONG_CLOSE or SHORT_CLOSE
    quantity: Decimal  # Quantity closed
    close_price: Decimal  # Price at which position was closed
    avg_open_price: Decimal  # Average price at which position was opened
    gross_proceeds: Decimal  # LONG: qty * close_price, SHORT: qty * avg_open_price
    cost_basis: Decimal  # LONG: qty * avg_open_price, SHORT: qty * close_price
    realized_pnl: Decimal  # gross_proceeds - cost_basis - fees
    fees: Decimal

    # Backwards compatibility aliases
    @property
    def quantity_sold(self) -> Decimal:
        return self.quantity

    @property
    def sale_price(self) -> Decimal:
        return self.close_price

    @property
    def avg_cost_price(self) -> Decimal:
        return self.avg_open_price

    @property
    def sale_proceeds(self) -> Decimal:
        return self.gross_proceeds


@dataclass
class RealizedPnLSummary:
    """Summary of realized P&L for a period or account."""

    total_realized_pnl: Decimal
    total_sales_proceeds: Decimal
    total_cost_basis: Decimal
    total_fees: Decimal
    transaction_count: int
    entries: list[RealizedPnLEntry]


@dataclass
class UnrealizedPnLEntry:
    """Single unrealized P&L entry for a position."""

    position_id: UUID
    asset_id: UUID
    ticker: str | None
    quantity: Decimal
    avg_price: Decimal
    total_cost: Decimal
    current_price: Decimal | None
    market_value: Decimal | None
    unrealized_pnl: Decimal | None
    unrealized_pnl_pct: Decimal | None


@dataclass
class UnrealizedPnLSummary:
    """Summary of unrealized P&L."""

    total_market_value: Decimal
    total_cost: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pnl_pct: Decimal | None
    positions_count: int
    positions_with_prices: int
    entries: list[UnrealizedPnLEntry]


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
        Calculate realized P&L from closing positions (LONG or SHORT).

        Implements NETTING model:
        - Only ONE position per asset (LONG or SHORT, never both)
        - SELL with LONG position → closes LONG, generates P&L
        - SELL with no LONG position → opens SHORT (no P&L)
        - BUY with SHORT position → closes SHORT, generates P&L
        - BUY with no SHORT position → opens/adds to LONG (no P&L)

        P&L Formulas:
        - LONG close: P&L = (sale_price - avg_long_cost) × quantity - fees
        - SHORT close: P&L = (avg_short_price - buy_price) × quantity - fees

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
            query = query.where(
                Transaction.executed_at
                >= datetime.combine(start_date, datetime.min.time())
            )

        if end_date:
            query = query.where(
                Transaction.executed_at
                <= datetime.combine(end_date, datetime.max.time())
            )

        result = await self.db.execute(query)
        transactions = list(result.scalars().all())

        # Group transactions by asset to calculate P&L per asset
        entries: list[RealizedPnLEntry] = []

        # Track position state per asset: position_type, quantity, total_cost
        asset_states: dict[UUID, dict] = {}

        for txn in transactions:
            aid = txn.asset_id

            # Initialize asset state if first transaction
            if aid not in asset_states:
                asset_states[aid] = {
                    "position_type": None,  # None, "LONG", or "SHORT"
                    "quantity": Decimal("0"),
                    "total_cost": Decimal("0"),
                }

            state = asset_states[aid]

            if txn.type in (TransactionType.BUY, TransactionType.SUBSCRIPTION):
                # BUY: closes SHORT or adds to LONG
                buy_qty = txn.quantity
                buy_price = txn.price
                fees = txn.fees

                if state["position_type"] == "SHORT":
                    # Closing SHORT position (BUY to cover)
                    short_qty = state["quantity"]
                    short_avg_price = state["total_cost"] / short_qty if short_qty > 0 else Decimal("0")

                    if buy_qty <= short_qty:
                        # Partial or full close of SHORT
                        # P&L = (short_sale_price - buy_price) × quantity - fees
                        qty_closed = buy_qty
                        gross_proceeds = qty_closed * short_avg_price  # We sold at this price
                        cost_basis = qty_closed * buy_price + fees  # We're buying back at this price
                        realized_pnl = gross_proceeds - cost_basis

                        entry = RealizedPnLEntry(
                            transaction_id=txn.id,
                            asset_id=aid,
                            ticker=txn.asset.ticker if txn.asset else None,
                            executed_at=txn.executed_at,
                            pnl_type=PnLType.SHORT_CLOSE,
                            quantity=qty_closed,
                            close_price=buy_price,  # Price at which we closed SHORT
                            avg_open_price=short_avg_price,  # Price at which we opened SHORT
                            gross_proceeds=gross_proceeds,
                            cost_basis=cost_basis,
                            realized_pnl=realized_pnl,
                            fees=fees,
                        )
                        entries.append(entry)

                        # Update state
                        state["quantity"] -= qty_closed
                        state["total_cost"] -= qty_closed * short_avg_price

                        if state["quantity"] <= Decimal("0"):
                            state["position_type"] = None
                            state["quantity"] = Decimal("0")
                            state["total_cost"] = Decimal("0")
                    else:
                        # Close SHORT fully and flip to LONG
                        # First: close all SHORT
                        qty_to_close_short = short_qty
                        if qty_to_close_short > 0:
                            gross_proceeds = qty_to_close_short * short_avg_price
                            # Proportional fees for closing SHORT
                            fees_for_short = fees * qty_to_close_short / buy_qty
                            cost_basis_short = qty_to_close_short * buy_price + fees_for_short
                            realized_pnl = gross_proceeds - cost_basis_short

                            entry = RealizedPnLEntry(
                                transaction_id=txn.id,
                                asset_id=aid,
                                ticker=txn.asset.ticker if txn.asset else None,
                                executed_at=txn.executed_at,
                                pnl_type=PnLType.SHORT_CLOSE,
                                quantity=qty_to_close_short,
                                close_price=buy_price,
                                avg_open_price=short_avg_price,
                                gross_proceeds=gross_proceeds,
                                cost_basis=cost_basis_short,
                                realized_pnl=realized_pnl,
                                fees=fees_for_short,
                            )
                            entries.append(entry)

                        # Then: open LONG with excess
                        excess = buy_qty - short_qty
                        fees_for_long = fees * excess / buy_qty
                        state["position_type"] = "LONG"
                        state["quantity"] = excess
                        state["total_cost"] = excess * buy_price + fees_for_long
                else:
                    # Adding to LONG or opening new LONG (no P&L event)
                    txn_cost = buy_qty * buy_price + fees
                    state["total_cost"] += txn_cost
                    state["quantity"] += buy_qty
                    state["position_type"] = "LONG"

            elif txn.type == TransactionType.SELL:
                # SELL: closes LONG or opens/adds to SHORT
                sell_qty = txn.quantity
                sell_price = txn.price
                fees = txn.fees

                if state["position_type"] == "LONG":
                    # Closing LONG position (SELL)
                    long_qty = state["quantity"]
                    long_avg_cost = state["total_cost"] / long_qty if long_qty > 0 else Decimal("0")

                    if sell_qty <= long_qty:
                        # Partial or full close of LONG
                        # P&L = (sale_price - avg_cost) × quantity - fees
                        qty_closed = sell_qty
                        gross_proceeds = qty_closed * sell_price - fees
                        cost_basis = qty_closed * long_avg_cost
                        realized_pnl = gross_proceeds - cost_basis

                        entry = RealizedPnLEntry(
                            transaction_id=txn.id,
                            asset_id=aid,
                            ticker=txn.asset.ticker if txn.asset else None,
                            executed_at=txn.executed_at,
                            pnl_type=PnLType.LONG_CLOSE,
                            quantity=qty_closed,
                            close_price=sell_price,  # Price at which we closed LONG
                            avg_open_price=long_avg_cost,  # Price at which we bought
                            gross_proceeds=gross_proceeds + fees,  # Gross before fees
                            cost_basis=cost_basis,
                            realized_pnl=realized_pnl,
                            fees=fees,
                        )
                        entries.append(entry)

                        # Update state
                        state["quantity"] -= qty_closed
                        state["total_cost"] -= qty_closed * long_avg_cost

                        if state["quantity"] <= Decimal("0"):
                            state["position_type"] = None
                            state["quantity"] = Decimal("0")
                            state["total_cost"] = Decimal("0")
                    else:
                        # Close LONG fully and flip to SHORT
                        # First: close all LONG
                        qty_to_close_long = long_qty
                        if qty_to_close_long > 0:
                            # Proportional fees for closing LONG
                            fees_for_long = fees * qty_to_close_long / sell_qty
                            gross_proceeds = qty_to_close_long * sell_price - fees_for_long
                            cost_basis = qty_to_close_long * long_avg_cost
                            realized_pnl = gross_proceeds - cost_basis

                            entry = RealizedPnLEntry(
                                transaction_id=txn.id,
                                asset_id=aid,
                                ticker=txn.asset.ticker if txn.asset else None,
                                executed_at=txn.executed_at,
                                pnl_type=PnLType.LONG_CLOSE,
                                quantity=qty_to_close_long,
                                close_price=sell_price,
                                avg_open_price=long_avg_cost,
                                gross_proceeds=gross_proceeds + fees_for_long,
                                cost_basis=cost_basis,
                                realized_pnl=realized_pnl,
                                fees=fees_for_long,
                            )
                            entries.append(entry)

                        # Then: open SHORT with excess
                        excess = sell_qty - long_qty
                        state["position_type"] = "SHORT"
                        state["quantity"] = excess
                        state["total_cost"] = excess * sell_price  # SHORT cost = sale price
                elif state["position_type"] == "SHORT":
                    # Adding to SHORT position (no P&L event)
                    state["quantity"] += sell_qty
                    state["total_cost"] += sell_qty * sell_price
                else:
                    # Opening new SHORT position (no P&L event)
                    state["position_type"] = "SHORT"
                    state["quantity"] = sell_qty
                    state["total_cost"] = sell_qty * sell_price

            elif txn.type == TransactionType.TRANSFER_IN:
                # Add to LONG position at given price (like BUY, no P&L)
                txn_cost = txn.quantity * txn.price
                if state["position_type"] == "SHORT":
                    # Transfer in reduces SHORT (treat like BUY without fees)
                    short_qty = state["quantity"]
                    if txn.quantity <= short_qty:
                        state["quantity"] -= txn.quantity
                        short_avg = state["total_cost"] / short_qty if short_qty > 0 else Decimal("0")
                        state["total_cost"] -= txn.quantity * short_avg
                        if state["quantity"] <= Decimal("0"):
                            state["position_type"] = None
                            state["quantity"] = Decimal("0")
                            state["total_cost"] = Decimal("0")
                    else:
                        excess = txn.quantity - short_qty
                        state["position_type"] = "LONG"
                        state["quantity"] = excess
                        state["total_cost"] = excess * txn.price
                else:
                    state["total_cost"] += txn_cost
                    state["quantity"] += txn.quantity
                    state["position_type"] = "LONG"

            elif txn.type == TransactionType.TRANSFER_OUT:
                # Reduce LONG position (similar to SELL but no P&L)
                if state["position_type"] == "LONG" and state["quantity"] > 0:
                    avg_cost = state["total_cost"] / state["quantity"]
                    if txn.quantity <= state["quantity"]:
                        state["total_cost"] -= txn.quantity * avg_cost
                        state["quantity"] -= txn.quantity
                        if state["quantity"] <= Decimal("0"):
                            state["position_type"] = None
                            state["quantity"] = Decimal("0")
                            state["total_cost"] = Decimal("0")

            elif txn.type == TransactionType.SPLIT:
                # Stock split: multiply quantity, keep total cost
                if txn.quantity > 0 and state["quantity"] > 0:
                    state["quantity"] = state["quantity"] * txn.quantity

        # Calculate totals
        total_pnl = sum(e.realized_pnl for e in entries)
        total_proceeds = sum(e.gross_proceeds for e in entries)
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

    async def calculate_unrealized_pnl(
        self,
        positions: list[Position],
        current_prices: dict[UUID, Decimal],
    ) -> UnrealizedPnLSummary:
        """
        Calculate unrealized P&L summary for open positions.

        Uses formula: unrealized_pnl = (current_price - avg_price) * quantity
        Which is equivalent to: market_value - total_cost

        Args:
            positions: List of Position objects with asset relationship loaded
            current_prices: Dictionary mapping asset_id -> current price

        Returns:
            UnrealizedPnLSummary with detailed entries and totals
        """
        logger.info(
            "calculate_unrealized_pnl_start",
            positions_count=len(positions),
            prices_count=len(current_prices),
        )

        entries: list[UnrealizedPnLEntry] = []
        total_market_value = Decimal("0")
        total_cost = Decimal("0")
        positions_with_prices = 0

        for pos in positions:
            if pos.quantity <= 0:
                continue

            ticker = pos.asset.ticker if hasattr(pos, "asset") and pos.asset else None
            current_price = current_prices.get(pos.asset_id)

            if current_price is not None:
                market_value = pos.quantity * current_price
                unrealized_pnl = market_value - pos.total_cost
                unrealized_pnl_pct = (
                    (unrealized_pnl / pos.total_cost * 100)
                    if pos.total_cost > 0
                    else Decimal("0")
                )
                total_market_value += market_value
                positions_with_prices += 1
            else:
                market_value = None
                unrealized_pnl = None
                unrealized_pnl_pct = None

            total_cost += pos.total_cost

            entry = UnrealizedPnLEntry(
                position_id=pos.id,
                asset_id=pos.asset_id,
                ticker=ticker,
                quantity=pos.quantity,
                avg_price=pos.avg_price,
                total_cost=pos.total_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
            )
            entries.append(entry)

        # Calculate totals
        total_unrealized_pnl = (
            total_market_value - total_cost
            if positions_with_prices > 0
            else Decimal("0")
        )
        total_unrealized_pnl_pct = (
            (total_unrealized_pnl / total_cost * 100)
            if total_cost > 0 and positions_with_prices > 0
            else None
        )

        summary = UnrealizedPnLSummary(
            total_market_value=total_market_value,
            total_cost=total_cost,
            total_unrealized_pnl=total_unrealized_pnl,
            total_unrealized_pnl_pct=total_unrealized_pnl_pct,
            positions_count=len(entries),
            positions_with_prices=positions_with_prices,
            entries=entries,
        )

        logger.info(
            "calculate_unrealized_pnl_complete",
            positions_count=len(entries),
            positions_with_prices=positions_with_prices,
            total_unrealized_pnl=str(total_unrealized_pnl),
        )

        return summary


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


async def calculate_unrealized_pnl(
    db: AsyncSession,
    positions: list[Position],
    current_prices: dict[UUID, Decimal],
) -> UnrealizedPnLSummary:
    """
    Utility function to calculate unrealized P&L.

    Args:
        db: Database session
        positions: List of Position objects with asset relationship loaded
        current_prices: Dictionary mapping asset_id -> current price

    Returns:
        UnrealizedPnLSummary with P&L details
    """
    service = PnLService(db)
    return await service.calculate_unrealized_pnl(
        positions=positions,
        current_prices=current_prices,
    )
