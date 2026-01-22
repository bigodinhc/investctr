"""
Position Reconciliation Service.

Reconciles positions from brokerage statements with database positions.
The statement is the source of truth for open positions.

Key operations:
- Compare current DB positions with statement positions
- Identify closed positions (no longer in statement)
- Record realized trades for closed positions
- Update positions from statement data
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from typing import Any

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Account, Asset, Position, RealizedTrade, Document, Transaction
from app.schemas.enums import PositionType, PositionSource, TransactionType

logger = get_logger(__name__)


@dataclass
class StatementPosition:
    """Represents a position from the statement."""
    ticker: str
    quantity: Decimal
    avg_price: Decimal
    total_cost: Decimal
    position_type: PositionType
    current_price: Decimal | None = None
    current_value: Decimal | None = None


@dataclass
class ReconciliationResult:
    """Result of position reconciliation."""
    positions_created: int
    positions_updated: int
    positions_closed: int
    realized_trades_created: int
    errors: list[str]


class PositionReconciliationService:
    """
    Service for reconciling positions from statements.

    The brokerage statement is considered the source of truth.
    When a new statement is imported:
    1. Positions in statement but not in DB → Create new position
    2. Positions in both → Update with statement data
    3. Positions in DB but not in statement → Close position, record realized trade
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def reconcile_positions(
        self,
        account_id: UUID,
        document_id: UUID,
        statement_positions: list[dict[str, Any]],
        statement_date: date | None = None,
    ) -> ReconciliationResult:
        """
        Reconcile positions from a statement with current database positions.

        Args:
            account_id: Account UUID
            document_id: Document UUID (for reference in realized trades)
            statement_positions: List of position dicts from statement
                Expected format: {ticker, quantity, avg_price, current_price?, current_value?}
            statement_date: Date of the statement (for close date on realized trades)

        Returns:
            ReconciliationResult with counts and errors
        """
        logger.info(
            "reconciliation_start",
            account_id=str(account_id),
            document_id=str(document_id),
            statement_positions_count=len(statement_positions),
        )

        result = ReconciliationResult(
            positions_created=0,
            positions_updated=0,
            positions_closed=0,
            realized_trades_created=0,
            errors=[],
        )

        # Parse statement positions into normalized format
        parsed_positions = await self._parse_statement_positions(statement_positions)

        # Get current positions for this account
        current_positions = await self._get_current_positions(account_id)

        # Build lookup maps
        statement_by_ticker: dict[str, StatementPosition] = {
            pos.ticker: pos for pos in parsed_positions
        }
        current_by_ticker: dict[str, Position] = {
            pos.asset.ticker: pos for pos in current_positions if pos.asset
        }

        # Identify positions to create, update, or close
        tickers_in_statement = set(statement_by_ticker.keys())
        tickers_in_db = set(current_by_ticker.keys())

        # New positions (in statement but not in DB)
        new_tickers = tickers_in_statement - tickers_in_db

        # Positions to update (in both)
        update_tickers = tickers_in_statement & tickers_in_db

        # Closed positions (in DB but not in statement)
        closed_tickers = tickers_in_db - tickers_in_statement

        # Process new positions
        for ticker in new_tickers:
            try:
                stmt_pos = statement_by_ticker[ticker]
                await self._create_position(
                    account_id=account_id,
                    ticker=ticker,
                    stmt_pos=stmt_pos,
                )
                result.positions_created += 1
            except Exception as e:
                result.errors.append(f"Failed to create position for {ticker}: {str(e)}")
                logger.error(
                    "reconciliation_create_error",
                    ticker=ticker,
                    error=str(e),
                )

        # Process positions to update
        for ticker in update_tickers:
            try:
                stmt_pos = statement_by_ticker[ticker]
                current_pos = current_by_ticker[ticker]
                await self._update_position(current_pos, stmt_pos)
                result.positions_updated += 1
            except Exception as e:
                result.errors.append(f"Failed to update position for {ticker}: {str(e)}")
                logger.error(
                    "reconciliation_update_error",
                    ticker=ticker,
                    error=str(e),
                )

        # Process closed positions
        for ticker in closed_tickers:
            try:
                current_pos = current_by_ticker[ticker]

                # Try to find closing price from transactions
                close_info = await self._find_close_info(
                    account_id=account_id,
                    asset_id=current_pos.asset_id,
                    document_id=document_id,
                )

                # Create realized trade record
                await self._create_realized_trade(
                    position=current_pos,
                    document_id=document_id,
                    close_date=statement_date or date.today(),
                    close_price=close_info.get("price"),
                )
                result.realized_trades_created += 1

                # Delete the position
                await self.db.delete(current_pos)
                result.positions_closed += 1

            except Exception as e:
                result.errors.append(f"Failed to close position for {ticker}: {str(e)}")
                logger.error(
                    "reconciliation_close_error",
                    ticker=ticker,
                    error=str(e),
                )

        await self.db.flush()

        logger.info(
            "reconciliation_complete",
            account_id=str(account_id),
            positions_created=result.positions_created,
            positions_updated=result.positions_updated,
            positions_closed=result.positions_closed,
            realized_trades_created=result.realized_trades_created,
            errors_count=len(result.errors),
        )

        return result

    async def _parse_statement_positions(
        self,
        raw_positions: list[dict[str, Any]],
    ) -> list[StatementPosition]:
        """Parse raw statement positions into StatementPosition objects."""
        parsed = []

        for raw in raw_positions:
            ticker = raw.get("ticker", "").upper().strip()
            if not ticker:
                continue

            # Parse quantity - handle both positive (LONG) and negative (SHORT)
            raw_quantity = raw.get("quantity", 0)
            try:
                quantity = Decimal(str(raw_quantity))
            except:
                continue

            if quantity == Decimal("0"):
                continue

            # Determine position type from quantity sign
            if quantity < 0:
                position_type = PositionType.SHORT
                quantity = abs(quantity)
            else:
                position_type = PositionType.LONG

            # Parse average price
            raw_avg_price = raw.get("avg_price") or raw.get("average_price") or raw.get("preco_medio") or 0
            try:
                avg_price = Decimal(str(raw_avg_price))
            except:
                avg_price = Decimal("0")

            # Calculate total cost
            raw_total = raw.get("total_cost") or raw.get("total") or raw.get("custo_total")
            if raw_total:
                try:
                    total_cost = Decimal(str(raw_total))
                except:
                    total_cost = quantity * avg_price
            else:
                total_cost = quantity * avg_price

            # Parse current price and value (optional)
            current_price = None
            current_value = None
            if raw.get("current_price"):
                try:
                    current_price = Decimal(str(raw.get("current_price")))
                except:
                    pass
            if raw.get("current_value"):
                try:
                    current_value = Decimal(str(raw.get("current_value")))
                except:
                    pass

            parsed.append(StatementPosition(
                ticker=ticker,
                quantity=quantity,
                avg_price=avg_price,
                total_cost=total_cost,
                position_type=position_type,
                current_price=current_price,
                current_value=current_value,
            ))

        return parsed

    async def _get_current_positions(self, account_id: UUID) -> list[Position]:
        """Get current positions for an account with asset data loaded."""
        query = (
            select(Position)
            .options(selectinload(Position.asset))
            .where(
                and_(
                    Position.account_id == account_id,
                    Position.quantity > 0,
                )
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _create_position(
        self,
        account_id: UUID,
        ticker: str,
        stmt_pos: StatementPosition,
    ) -> Position:
        """Create a new position from statement data."""
        # Get or create asset
        asset = await self._get_or_create_asset(ticker)

        position = Position(
            account_id=account_id,
            asset_id=asset.id,
            quantity=stmt_pos.quantity,
            avg_price=stmt_pos.avg_price,
            total_cost=stmt_pos.total_cost,
            position_type=stmt_pos.position_type,
            source=PositionSource.STATEMENT.value,
            updated_at=datetime.utcnow(),
        )

        self.db.add(position)
        await self.db.flush()

        logger.info(
            "position_created_from_statement",
            ticker=ticker,
            quantity=str(stmt_pos.quantity),
            avg_price=str(stmt_pos.avg_price),
        )

        return position

    async def _update_position(
        self,
        position: Position,
        stmt_pos: StatementPosition,
    ) -> None:
        """Update existing position with statement data."""
        # Update position fields
        position.quantity = stmt_pos.quantity
        position.avg_price = stmt_pos.avg_price
        position.total_cost = stmt_pos.total_cost
        position.position_type = stmt_pos.position_type
        position.source = PositionSource.STATEMENT.value
        position.updated_at = datetime.utcnow()

        logger.debug(
            "position_updated_from_statement",
            ticker=position.asset.ticker if position.asset else "unknown",
            quantity=str(stmt_pos.quantity),
            avg_price=str(stmt_pos.avg_price),
        )

    async def _create_realized_trade(
        self,
        position: Position,
        document_id: UUID,
        close_date: date,
        close_price: Decimal | None = None,
    ) -> RealizedTrade:
        """Create a realized trade record for a closed position."""
        # If no close price provided, use avg_price as estimate
        actual_close_price = close_price or position.avg_price

        # Calculate realized P&L
        if position.position_type == PositionType.LONG:
            # LONG: P&L = (close_price - avg_price) * quantity
            realized_pnl = (actual_close_price - position.avg_price) * position.quantity
        else:
            # SHORT: P&L = (avg_price - close_price) * quantity
            realized_pnl = (position.avg_price - actual_close_price) * position.quantity

        # Calculate percentage
        if position.total_cost and position.total_cost != Decimal("0"):
            realized_pnl_pct = (realized_pnl / abs(position.total_cost)) * 100
        else:
            realized_pnl_pct = Decimal("0")

        realized_trade = RealizedTrade(
            account_id=position.account_id,
            asset_id=position.asset_id,
            open_quantity=position.quantity,
            open_avg_price=position.avg_price,
            open_date=position.opened_at.date() if position.opened_at else None,
            close_quantity=position.quantity,
            close_avg_price=actual_close_price,
            close_date=close_date,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            document_id=document_id,
            notes=f"Position closed - not present in statement dated {close_date}",
        )

        self.db.add(realized_trade)

        logger.info(
            "realized_trade_created",
            asset_id=str(position.asset_id),
            ticker=position.asset.ticker if position.asset else "unknown",
            quantity=str(position.quantity),
            realized_pnl=str(realized_pnl),
            realized_pnl_pct=str(realized_pnl_pct),
        )

        return realized_trade

    async def _find_close_info(
        self,
        account_id: UUID,
        asset_id: UUID,
        document_id: UUID,
    ) -> dict[str, Any]:
        """
        Try to find closing price from transactions in the same document.

        Returns dict with 'price' key if found, empty dict otherwise.
        """
        # Look for SELL transactions for this asset in this document
        query = (
            select(Transaction)
            .where(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.asset_id == asset_id,
                    Transaction.document_id == document_id,
                    Transaction.type == TransactionType.SELL,
                )
            )
            .order_by(Transaction.executed_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        transaction = result.scalar_one_or_none()

        if transaction and transaction.price:
            return {"price": transaction.price}

        return {}

    async def _get_or_create_asset(self, ticker: str) -> Asset:
        """Get existing asset or create a minimal one."""
        from app.schemas.enums import AssetType

        query = select(Asset).where(Asset.ticker == ticker.upper())
        result = await self.db.execute(query)
        asset = result.scalar_one_or_none()

        if asset:
            return asset

        # Create minimal asset - type will be inferred
        asset_type = self._infer_asset_type(ticker)

        asset = Asset(
            ticker=ticker.upper(),
            name=ticker.upper(),  # Will be updated later
            asset_type=asset_type,
            currency="BRL" if self._is_brazilian_ticker(ticker) else "USD",
        )
        self.db.add(asset)
        await self.db.flush()

        return asset

    def _is_brazilian_ticker(self, ticker: str) -> bool:
        """Check if a ticker looks like a Brazilian (B3) ticker."""
        ticker = ticker.upper()
        if len(ticker) >= 4 and len(ticker) <= 6:
            if ticker[-1].isdigit():
                letter_part = ticker.rstrip("0123456789")
                if len(letter_part) >= 3 and letter_part.isalpha():
                    return True
        return False

    def _infer_asset_type(self, ticker: str) -> "AssetType":
        """Infer asset type from ticker pattern."""
        from app.schemas.enums import AssetType

        ticker = ticker.upper()

        if not self._is_brazilian_ticker(ticker):
            return AssetType.STOCK

        # Get the numeric suffix
        numeric_part = ""
        for char in reversed(ticker):
            if char.isdigit():
                numeric_part = char + numeric_part
            else:
                break

        if numeric_part:
            num = int(numeric_part)
            if num == 11:
                return AssetType.FII
            if num in (34, 35):
                return AssetType.BDR

        return AssetType.STOCK

    async def migrate_positions_from_statement(
        self,
        account_id: UUID,
        document_id: UUID,
        statement_positions: list[dict[str, Any]],
    ) -> ReconciliationResult:
        """
        Migrate positions from a statement, replacing all existing positions.

        This is used for initial migration from statements to the new architecture.
        Unlike reconcile_positions, this does NOT create realized trades for
        positions being replaced (since we're just syncing from statement).

        Args:
            account_id: Account UUID
            document_id: Document UUID (for reference)
            statement_positions: List of position dicts from statement

        Returns:
            ReconciliationResult with counts and errors
        """
        logger.info(
            "migration_start",
            account_id=str(account_id),
            document_id=str(document_id),
            statement_positions_count=len(statement_positions),
        )

        result = ReconciliationResult(
            positions_created=0,
            positions_updated=0,
            positions_closed=0,
            realized_trades_created=0,
            errors=[],
        )

        # Parse statement positions
        parsed_positions = await self._parse_statement_positions(statement_positions)

        if not parsed_positions:
            logger.warning("migration_no_positions", account_id=str(account_id))
            return result

        # Delete all existing positions for this account (clean slate)
        delete_stmt = delete(Position).where(Position.account_id == account_id)
        await self.db.execute(delete_stmt)
        result.positions_closed = 0  # We're not tracking closed as realized trades

        # Create new positions from statement
        for stmt_pos in parsed_positions:
            try:
                await self._create_position(
                    account_id=account_id,
                    ticker=stmt_pos.ticker,
                    stmt_pos=stmt_pos,
                )
                result.positions_created += 1
            except Exception as e:
                result.errors.append(f"Failed to create position for {stmt_pos.ticker}: {str(e)}")
                logger.error(
                    "migration_create_error",
                    ticker=stmt_pos.ticker,
                    error=str(e),
                )

        await self.db.flush()

        logger.info(
            "migration_complete",
            account_id=str(account_id),
            positions_created=result.positions_created,
            errors_count=len(result.errors),
        )

        return result


# Utility function for external use
async def reconcile_account_positions(
    db: AsyncSession,
    account_id: UUID,
    document_id: UUID,
    statement_positions: list[dict[str, Any]],
    statement_date: date | None = None,
) -> ReconciliationResult:
    """
    Utility function to reconcile positions for an account.

    Args:
        db: Database session
        account_id: Account UUID
        document_id: Document UUID
        statement_positions: List of position dicts from statement
        statement_date: Date of the statement

    Returns:
        ReconciliationResult
    """
    service = PositionReconciliationService(db)
    return await service.reconcile_positions(
        account_id=account_id,
        document_id=document_id,
        statement_positions=statement_positions,
        statement_date=statement_date,
    )
