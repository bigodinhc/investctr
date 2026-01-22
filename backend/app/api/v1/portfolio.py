"""
Portfolio management endpoints.

Provides aggregated portfolio views and summaries with realized and unrealized P&L.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import AuthenticatedUser, DBSession
from app.core.logging import get_logger
from app.models import Account, Position, PortfolioSnapshot, FixedIncomePosition, InvestmentFundPosition
from app.schemas.enums import AccountType, AssetType

# Mapping from AccountType to broker display name
ACCOUNT_TYPE_BROKER_MAP: dict[AccountType, str] = {
    AccountType.BTG_BR: "BTG Pactual",
    AccountType.XP: "XP Investimentos",
    AccountType.BTG_CAYMAN: "BTG Pactual (Cayman)",
    AccountType.TESOURO_DIRETO: "Tesouro Direto",
}
from app.schemas.fund import PortfolioHistoryItem, PortfolioHistoryResponse
from app.services.pnl_service import PnLService
from app.services.quote_service import QuoteService
from app.services.exchange_rate_service import ExchangeRateService

logger = get_logger(__name__)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# -------------------------------------------------------------------------
# Response Schemas
# -------------------------------------------------------------------------


class AssetTypeSummary(BaseModel):
    """Summary for a specific asset type."""

    asset_type: AssetType
    positions_count: int
    total_cost: Decimal
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    allocation_pct: Decimal | None = Field(None, description="% of total portfolio")


class AllocationItem(BaseModel):
    """Single allocation item for charts."""

    name: str = Field(..., description="Category name (asset type or asset)")
    value: Decimal = Field(..., description="Market value or cost basis")
    percentage: Decimal = Field(..., description="Allocation percentage (0-100)")
    color: str | None = Field(None, description="Suggested color for chart")


class AllocationResponse(BaseModel):
    """Portfolio allocation response for charting."""

    by_asset_type: list[AllocationItem] = Field(
        default_factory=list,
        description="Allocation grouped by asset type",
    )
    by_asset: list[AllocationItem] = Field(
        default_factory=list,
        description="Allocation by individual asset (top positions)",
    )
    total_value: Decimal = Field(..., description="Total portfolio value")
    positions_count: int = Field(..., description="Total number of positions")


class AccountSummary(BaseModel):
    """Summary for a specific account."""

    account_id: UUID
    account_name: str
    broker: str | None = None
    positions_count: int
    total_cost: Decimal
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    allocation_pct: Decimal | None = Field(None, description="% of total portfolio")


class CategoryBreakdown(BaseModel):
    """Category breakdown from brokerage statement (source of truth)."""

    renda_fixa: Decimal = Field(default=Decimal("0"), description="Fixed income total")
    fundos_investimento: Decimal = Field(
        default=Decimal("0"), description="Investment funds total"
    )
    renda_variavel: Decimal = Field(
        default=Decimal("0"), description="Variable income (stocks) total"
    )
    derivativos: Decimal = Field(default=Decimal("0"), description="Derivatives total")
    conta_corrente: Decimal = Field(
        default=Decimal("0"), description="Checking account balance"
    )
    coe: Decimal = Field(default=Decimal("0"), description="COE total")


class PortfolioSummaryResponse(BaseModel):
    """Comprehensive portfolio summary response."""

    # Totals (from PortfolioSnapshot - source of truth)
    total_positions: int = Field(..., description="Total number of positions")
    total_value: Decimal = Field(
        ..., description="Total portfolio value (from brokerage statement)"
    )
    total_cost: Decimal = Field(..., description="Total cost basis")
    total_unrealized_pnl: Decimal = Field(..., description="Total unrealized P&L")
    total_unrealized_pnl_pct: Decimal | None = Field(
        None, description="Total unrealized P&L %"
    )
    total_realized_pnl: Decimal = Field(
        ..., description="Total realized P&L (all time)"
    )

    # Category breakdown from statement (source of truth)
    category_breakdown: CategoryBreakdown | None = Field(
        None, description="Category breakdown from brokerage statement"
    )
    snapshot_date: date | None = Field(
        None, description="Date of the latest portfolio snapshot"
    )

    # Position counts by type
    long_positions_count: int = Field(
        default=0, description="Number of long positions"
    )
    short_positions_count: int = Field(
        default=0, description="Number of short positions"
    )

    # Exposure metrics (for long/short portfolios)
    long_value: Decimal = Field(
        default=Decimal("0"), description="Market value of long positions"
    )
    short_value: Decimal = Field(
        default=Decimal("0"), description="Market value of short positions"
    )
    gross_exposure: Decimal = Field(
        default=Decimal("0"), description="Long + Short (absolute, total risk)"
    )
    net_exposure: Decimal = Field(
        default=Decimal("0"), description="Long - Short (directional risk)"
    )
    gross_exposure_pct: Decimal | None = Field(
        None, description="Gross exposure as % of NAV (>100% = leveraged)"
    )
    net_exposure_pct: Decimal | None = Field(
        None, description="Net exposure as % of NAV (market direction bias)"
    )

    # Breakdowns
    by_asset_type: list[AssetTypeSummary] = Field(
        default_factory=list,
        description="Summary grouped by asset type",
    )
    by_account: list[AccountSummary] = Field(
        default_factory=list,
        description="Summary grouped by account (only if not filtered by account)",
    )

    # Metadata
    accounts_count: int = Field(..., description="Number of accounts included")
    last_price_update: datetime | None = Field(
        None, description="Latest quote timestamp"
    )


# -------------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------------


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    user: AuthenticatedUser,
    db: DBSession,
    account_id: UUID | None = Query(None, description="Filter by specific account"),
) -> PortfolioSummaryResponse:
    """
    Get comprehensive portfolio summary.

    Returns aggregated portfolio metrics including:
    - Total value from latest PortfolioSnapshot (source of truth from brokerage)
    - Category breakdown from statement
    - Total realized P&L (from all sales)
    - Breakdown by asset type
    - Breakdown by account (if not filtered)

    If account_id is provided, returns summary for that account only.
    Otherwise, returns consolidated summary across all user accounts.
    """
    # First, fetch the latest PortfolioSnapshot (source of truth from statement)
    snapshot_query = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user.id)
        .order_by(PortfolioSnapshot.date.desc())
        .limit(1)
    )
    if account_id:
        snapshot_query = snapshot_query.where(PortfolioSnapshot.account_id == account_id)

    snapshot_result = await db.execute(snapshot_query)
    latest_snapshot = snapshot_result.scalar_one_or_none()

    # Build category breakdown from snapshot if available
    category_breakdown: CategoryBreakdown | None = None
    snapshot_date: date | None = None

    if latest_snapshot:
        category_breakdown = CategoryBreakdown(
            renda_fixa=latest_snapshot.renda_fixa or Decimal("0"),
            fundos_investimento=latest_snapshot.fundos_investimento or Decimal("0"),
            renda_variavel=latest_snapshot.renda_variavel or Decimal("0"),
            derivativos=latest_snapshot.derivativos or Decimal("0"),
            conta_corrente=latest_snapshot.conta_corrente or Decimal("0"),
            coe=latest_snapshot.coe or Decimal("0"),
        )
        snapshot_date = latest_snapshot.date

    # Build base query for stock positions (for position counts and breakdowns)
    base_query = (
        select(Position)
        .join(Position.account)
        .join(Position.asset)
        .options(selectinload(Position.asset), selectinload(Position.account))
        .where(Account.user_id == user.id)
        .where(Position.quantity > 0)
    )

    if account_id:
        base_query = base_query.where(Position.account_id == account_id)

    result = await db.execute(base_query)
    positions = list(result.scalars().all())

    # Query fixed income positions - get only the latest by maturity date for each asset
    # to avoid counting expired/duplicated positions
    today = date.today()
    fi_query = (
        select(FixedIncomePosition)
        .join(FixedIncomePosition.account)
        .options(selectinload(FixedIncomePosition.account))
        .where(Account.user_id == user.id)
        # Filter out matured positions
        .where(
            (FixedIncomePosition.maturity_date >= today) |
            (FixedIncomePosition.maturity_date.is_(None))
        )
    )
    if account_id:
        fi_query = fi_query.where(FixedIncomePosition.account_id == account_id)

    fi_result = await db.execute(fi_query)
    fixed_income_positions = list(fi_result.scalars().all())

    # Query investment fund positions
    fund_query = (
        select(InvestmentFundPosition)
        .join(InvestmentFundPosition.account)
        .options(selectinload(InvestmentFundPosition.account))
        .where(Account.user_id == user.id)
    )
    if account_id:
        fund_query = fund_query.where(InvestmentFundPosition.account_id == account_id)

    fund_result = await db.execute(fund_query)
    investment_fund_positions = list(fund_result.scalars().all())

    # Check if we have any positions at all
    total_positions_count = len(positions) + len(fixed_income_positions) + len(investment_fund_positions)

    if total_positions_count == 0 and not latest_snapshot:
        return PortfolioSummaryResponse(
            total_positions=0,
            total_value=Decimal("0"),
            total_cost=Decimal("0"),
            total_unrealized_pnl=Decimal("0"),
            total_unrealized_pnl_pct=None,
            total_realized_pnl=Decimal("0"),
            category_breakdown=None,
            snapshot_date=None,
            long_positions_count=0,
            short_positions_count=0,
            long_value=Decimal("0"),
            short_value=Decimal("0"),
            gross_exposure=Decimal("0"),
            net_exposure=Decimal("0"),
            gross_exposure_pct=None,
            net_exposure_pct=None,
            by_asset_type=[],
            by_account=[],
            accounts_count=0,
            last_price_update=None,
        )

    # Get current prices for all assets
    asset_ids = list(set(pos.asset_id for pos in positions))
    quote_service = QuoteService(db)
    current_prices = await quote_service.get_latest_prices(asset_ids)

    # Calculate unrealized P&L
    pnl_service = PnLService(db)
    unrealized_summary = await pnl_service.calculate_unrealized_pnl(
        positions, current_prices
    )

    # Calculate realized P&L
    realized_summary = await pnl_service.calculate_realized_pnl(
        account_id=account_id,
        user_id=user.id if not account_id else None,
    )

    # Build lookup maps
    unrealized_by_position = {
        entry.position_id: entry for entry in unrealized_summary.entries
    }

    # Calculate fixed income and fund totals (needed for both branches)
    fi_total_value = sum(fi.total_value for fi in fixed_income_positions)
    fund_total_value = sum(
        fi.net_balance if fi.net_balance is not None else fi.gross_balance
        for fi in investment_fund_positions
    )

    # If we have a snapshot, use its NAV as total_value (source of truth)
    # Otherwise, fall back to calculated values
    if latest_snapshot and latest_snapshot.nav > 0:
        # Use snapshot NAV as source of truth
        total_value = latest_snapshot.nav
        total_cost = latest_snapshot.total_cost or latest_snapshot.nav
    else:
        # Fall back to calculated values (legacy behavior)
        total_cost = unrealized_summary.total_cost
        stock_market_value = unrealized_summary.total_market_value
        if stock_market_value == 0 and unrealized_summary.total_cost > 0:
            stock_market_value = unrealized_summary.total_cost
        total_market_value = stock_market_value

        # Add fixed income totals (only unique positions)
        total_cost += fi_total_value
        total_market_value += fi_total_value

        # Add investment fund totals
        total_cost += fund_total_value
        total_market_value += fund_total_value

        total_value = total_market_value if total_market_value > 0 else total_cost

    total_unrealized_pnl = unrealized_summary.total_unrealized_pnl
    total_unrealized_pnl_pct = unrealized_summary.total_unrealized_pnl_pct

    # Group by asset type
    by_asset_type_data: dict[AssetType, dict] = {}

    # Add stock positions
    for pos in positions:
        asset_type = pos.asset.asset_type
        pnl_entry = unrealized_by_position.get(pos.id)

        if asset_type not in by_asset_type_data:
            by_asset_type_data[asset_type] = {
                "positions_count": 0,
                "total_cost": Decimal("0"),
                "market_value": Decimal("0"),
            }

        data = by_asset_type_data[asset_type]
        data["positions_count"] += 1
        data["total_cost"] += pos.total_cost

        if pnl_entry and pnl_entry.market_value is not None:
            data["market_value"] += pnl_entry.market_value

    # Add fixed income positions (use BOND as asset type)
    if fixed_income_positions:
        if AssetType.BOND not in by_asset_type_data:
            by_asset_type_data[AssetType.BOND] = {
                "positions_count": 0,
                "total_cost": Decimal("0"),
                "market_value": Decimal("0"),
            }
        by_asset_type_data[AssetType.BOND]["positions_count"] += len(fixed_income_positions)
        by_asset_type_data[AssetType.BOND]["total_cost"] += fi_total_value
        by_asset_type_data[AssetType.BOND]["market_value"] += fi_total_value

    # Add investment fund positions (use FUND as asset type)
    if investment_fund_positions:
        if AssetType.FUND not in by_asset_type_data:
            by_asset_type_data[AssetType.FUND] = {
                "positions_count": 0,
                "total_cost": Decimal("0"),
                "market_value": Decimal("0"),
            }
        by_asset_type_data[AssetType.FUND]["positions_count"] += len(investment_fund_positions)
        by_asset_type_data[AssetType.FUND]["total_cost"] += fund_total_value
        by_asset_type_data[AssetType.FUND]["market_value"] += fund_total_value

    # Build by_asset_type response
    by_asset_type = []
    for asset_type, data in by_asset_type_data.items():
        market_value = data["market_value"] if data["market_value"] > 0 else None
        unrealized_pnl = (
            data["market_value"] - data["total_cost"]
            if data["market_value"] > 0
            else None
        )
        unrealized_pnl_pct = (
            (unrealized_pnl / data["total_cost"] * 100)
            if unrealized_pnl is not None and data["total_cost"] > 0
            else None
        )
        allocation_pct = (
            (data["total_cost"] / total_cost * 100) if total_cost > 0 else None
        )

        by_asset_type.append(
            AssetTypeSummary(
                asset_type=asset_type,
                positions_count=data["positions_count"],
                total_cost=data["total_cost"],
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                allocation_pct=allocation_pct,
            )
        )

    # Sort by allocation descending
    by_asset_type.sort(key=lambda x: x.total_cost, reverse=True)

    # Group by account (only if not filtered by account_id)
    by_account = []
    if not account_id:
        by_account_data: dict[UUID, dict] = {}
        for pos in positions:
            acc_id = pos.account_id
            pnl_entry = unrealized_by_position.get(pos.id)

            if acc_id not in by_account_data:
                by_account_data[acc_id] = {
                    "account": pos.account,
                    "positions_count": 0,
                    "total_cost": Decimal("0"),
                    "market_value": Decimal("0"),
                }

            data = by_account_data[acc_id]
            data["positions_count"] += 1
            data["total_cost"] += pos.total_cost

            if pnl_entry and pnl_entry.market_value is not None:
                data["market_value"] += pnl_entry.market_value

        for acc_id, data in by_account_data.items():
            market_value = data["market_value"] if data["market_value"] > 0 else None
            unrealized_pnl = (
                data["market_value"] - data["total_cost"]
                if data["market_value"] > 0
                else None
            )
            unrealized_pnl_pct = (
                (unrealized_pnl / data["total_cost"] * 100)
                if unrealized_pnl is not None and data["total_cost"] > 0
                else None
            )
            allocation_pct = (
                (data["total_cost"] / total_cost * 100) if total_cost > 0 else None
            )

            by_account.append(
                AccountSummary(
                    account_id=acc_id,
                    account_name=data["account"].name,
                    broker=ACCOUNT_TYPE_BROKER_MAP.get(data["account"].type),
                    positions_count=data["positions_count"],
                    total_cost=data["total_cost"],
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    allocation_pct=allocation_pct,
                )
            )

        # Sort by allocation descending
        by_account.sort(key=lambda x: x.total_cost, reverse=True)

    # Count unique accounts (include all position types)
    unique_accounts = set(pos.account_id for pos in positions)
    unique_accounts.update(fi.account_id for fi in fixed_income_positions)
    unique_accounts.update(fund.account_id for fund in investment_fund_positions)

    # Calculate exposure metrics
    # When using snapshot, get values from category breakdown; otherwise use calculated
    if latest_snapshot and category_breakdown:
        # Use snapshot category values for exposure calculation
        fi_value = category_breakdown.renda_fixa
        fund_value = category_breakdown.fundos_investimento
        rv_value = category_breakdown.renda_variavel
        derivativos_value = category_breakdown.derivativos

        stock_long_value = rv_value  # RV is stocks
        stock_short_value = abs(min(derivativos_value, Decimal("0")))  # Derivatives can be negative

        long_value = stock_long_value + fi_value + fund_value
        short_value = stock_short_value
    else:
        # Fall back to calculated values
        stock_long_value = unrealized_summary.long_value
        stock_short_value = unrealized_summary.short_value

        # Calculate fixed income and fund values for positions
        fi_value = sum(fi.total_value for fi in fixed_income_positions)
        fund_value = sum(
            f.net_balance if f.net_balance is not None else f.gross_balance
            for f in investment_fund_positions
        )

        long_value = stock_long_value + fi_value + fund_value
        short_value = stock_short_value

    gross_exposure = long_value + short_value
    net_exposure = long_value - short_value

    # Calculate exposure percentages (relative to total value/NAV)
    gross_exposure_pct = (
        (gross_exposure / total_value * 100) if total_value > 0 else None
    )
    net_exposure_pct = (
        (net_exposure / total_value * 100) if total_value > 0 else None
    )

    return PortfolioSummaryResponse(
        total_positions=total_positions_count,
        total_value=total_value,
        total_cost=total_cost,
        total_unrealized_pnl=total_unrealized_pnl,
        total_unrealized_pnl_pct=total_unrealized_pnl_pct,
        total_realized_pnl=realized_summary.total_realized_pnl,
        category_breakdown=category_breakdown,
        snapshot_date=snapshot_date,
        long_positions_count=unrealized_summary.long_positions_count + len(fixed_income_positions) + len(investment_fund_positions),
        short_positions_count=unrealized_summary.short_positions_count,
        long_value=long_value,
        short_value=short_value,
        gross_exposure=gross_exposure,
        net_exposure=net_exposure,
        gross_exposure_pct=gross_exposure_pct,
        net_exposure_pct=net_exposure_pct,
        by_asset_type=by_asset_type,
        by_account=by_account,
        accounts_count=len(unique_accounts),
        last_price_update=None,  # TODO: Get from latest quote timestamp
    )


# -------------------------------------------------------------------------
# Allocation Endpoint
# -------------------------------------------------------------------------

# Color palette for asset types (gold-themed)
ASSET_TYPE_COLORS: dict[AssetType, str] = {
    AssetType.STOCK: "#D4AF37",  # Gold
    AssetType.ETF: "#B8860B",  # Dark golden rod
    AssetType.REIT: "#DAA520",  # Goldenrod
    AssetType.BDR: "#FFD700",  # Gold (bright)
    AssetType.FUND: "#F0E68C",  # Khaki
    AssetType.FII: "#C5B358",  # Vegas gold
    AssetType.FIAGRO: "#E6BE8A",  # Pale gold
    AssetType.BOND: "#EEE8AA",  # Pale goldenrod
    AssetType.TREASURY: "#FAFAD2",  # Light goldenrod yellow
    AssetType.CRYPTO: "#CD853F",  # Peru
    AssetType.OPTION: "#D2691E",  # Chocolate
    AssetType.FUTURE: "#8B4513",  # Saddle brown
}


@router.get("/allocation", response_model=AllocationResponse)
async def get_portfolio_allocation(
    user: AuthenticatedUser,
    db: DBSession,
    account_id: UUID | None = Query(None, description="Filter by specific account"),
    top_assets: int = Query(
        10, ge=1, le=50, description="Number of top assets to return"
    ),
) -> AllocationResponse:
    """
    Get portfolio allocation for charting.

    Returns allocation breakdown by:
    - Asset type (for donut chart)
    - Individual assets (top N by value)

    Uses market value when available, otherwise falls back to cost basis.
    """
    # Build base query for stock positions
    base_query = (
        select(Position)
        .join(Position.account)
        .join(Position.asset)
        .options(selectinload(Position.asset), selectinload(Position.account))
        .where(Account.user_id == user.id)
        .where(Position.quantity > 0)
    )

    if account_id:
        base_query = base_query.where(Position.account_id == account_id)

    result = await db.execute(base_query)
    positions = list(result.scalars().all())

    # Query fixed income positions
    fi_query = (
        select(FixedIncomePosition)
        .join(FixedIncomePosition.account)
        .where(Account.user_id == user.id)
    )
    if account_id:
        fi_query = fi_query.where(FixedIncomePosition.account_id == account_id)

    fi_result = await db.execute(fi_query)
    fixed_income_positions = list(fi_result.scalars().all())

    # Query investment fund positions
    fund_query = (
        select(InvestmentFundPosition)
        .join(InvestmentFundPosition.account)
        .where(Account.user_id == user.id)
    )
    if account_id:
        fund_query = fund_query.where(InvestmentFundPosition.account_id == account_id)

    fund_result = await db.execute(fund_query)
    investment_fund_positions = list(fund_result.scalars().all())

    total_positions_count = len(positions) + len(fixed_income_positions) + len(investment_fund_positions)

    if total_positions_count == 0:
        return AllocationResponse(
            by_asset_type=[],
            by_asset=[],
            total_value=Decimal("0"),
            positions_count=0,
        )

    # Get current prices for stock assets
    asset_ids = list(set(pos.asset_id for pos in positions))
    quote_service = QuoteService(db)
    current_prices = await quote_service.get_latest_prices(asset_ids) if asset_ids else {}

    # Calculate values for each stock position
    position_values: list[tuple[Position, Decimal]] = []
    for pos in positions:
        # Use market value if price available, otherwise use cost
        price_info = current_prices.get(pos.asset_id)
        if price_info and price_info.get("price"):
            value = pos.quantity * price_info["price"]
        else:
            value = pos.total_cost
        position_values.append((pos, value))

    # Calculate total value (including fixed income and funds)
    total_value = sum(v for _, v in position_values)

    # Add fixed income values
    fi_total_value = sum(fi.total_value for fi in fixed_income_positions)
    total_value += fi_total_value

    # Add investment fund values
    fund_total_value = sum(
        fi.net_balance if fi.net_balance is not None else fi.gross_balance
        for fi in investment_fund_positions
    )
    total_value += fund_total_value

    if total_value <= 0:
        return AllocationResponse(
            by_asset_type=[],
            by_asset=[],
            total_value=Decimal("0"),
            positions_count=total_positions_count,
        )

    # Group by asset type
    by_type_data: dict[AssetType, Decimal] = {}

    # Add stock positions by type
    for pos, value in position_values:
        asset_type = pos.asset.asset_type
        by_type_data[asset_type] = by_type_data.get(asset_type, Decimal("0")) + value

    # Add fixed income as BOND type
    if fi_total_value > 0:
        by_type_data[AssetType.BOND] = by_type_data.get(AssetType.BOND, Decimal("0")) + fi_total_value

    # Add investment funds as FUND type
    if fund_total_value > 0:
        by_type_data[AssetType.FUND] = by_type_data.get(AssetType.FUND, Decimal("0")) + fund_total_value

    by_asset_type = [
        AllocationItem(
            name=asset_type.value,
            value=value,
            percentage=round(value / total_value * 100, 2),
            color=ASSET_TYPE_COLORS.get(asset_type),
        )
        for asset_type, value in sorted(
            by_type_data.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    ]

    # Group by individual asset (top N)
    by_asset_data: dict[str, tuple[str, Decimal]] = {}

    # Add stock positions
    for pos, value in position_values:
        ticker = pos.asset.ticker
        name = pos.asset.name or ticker
        if ticker in by_asset_data:
            existing_name, existing_value = by_asset_data[ticker]
            by_asset_data[ticker] = (existing_name, existing_value + value)
        else:
            by_asset_data[ticker] = (name, value)

    # Add fixed income positions
    for fi in fixed_income_positions:
        key = f"FI:{fi.asset_name[:20]}"  # Truncate long names
        name = fi.asset_name
        value = fi.total_value
        if key in by_asset_data:
            existing_name, existing_value = by_asset_data[key]
            by_asset_data[key] = (existing_name, existing_value + value)
        else:
            by_asset_data[key] = (name, value)

    # Add investment fund positions
    for fund in investment_fund_positions:
        key = f"FD:{fund.fund_name[:20]}"  # Truncate long names
        name = fund.fund_name
        value = fund.net_balance if fund.net_balance is not None else fund.gross_balance
        if key in by_asset_data:
            existing_name, existing_value = by_asset_data[key]
            by_asset_data[key] = (existing_name, existing_value + value)
        else:
            by_asset_data[key] = (name, value)

    # Sort by value and take top N
    sorted_assets = sorted(
        by_asset_data.items(),
        key=lambda x: x[1][1],
        reverse=True,
    )[:top_assets]

    by_asset = [
        AllocationItem(
            name=f"{ticker} - {name}" if not ticker.startswith(("FI:", "FD:")) else name,
            value=value,
            percentage=round(value / total_value * 100, 2),
            color=None,  # Let frontend assign colors
        )
        for ticker, (name, value) in sorted_assets
    ]

    return AllocationResponse(
        by_asset_type=by_asset_type,
        by_asset=by_asset,
        total_value=total_value,
        positions_count=total_positions_count,
    )


# -------------------------------------------------------------------------
# History Endpoint
# -------------------------------------------------------------------------


# Period options for history
PeriodType = Literal["1M", "3M", "6M", "1Y", "YTD", "MAX"]


def _get_period_start_date(period: PeriodType) -> date:
    """Calculate the start date for a given period."""
    today = date.today()

    if period == "1M":
        return today - timedelta(days=30)
    elif period == "3M":
        return today - timedelta(days=90)
    elif period == "6M":
        return today - timedelta(days=180)
    elif period == "1Y":
        return today - timedelta(days=365)
    elif period == "YTD":
        return today.replace(month=1, day=1)
    else:  # MAX
        return date(2000, 1, 1)  # Far enough back to get all data


@router.get("/history", response_model=PortfolioHistoryResponse)
async def get_portfolio_history(
    user: AuthenticatedUser,
    db: DBSession,
    period: PeriodType = Query(
        "YTD", description="Period for history (1M, 3M, 6M, 1Y, YTD, MAX)"
    ),
    account_id: UUID | None = Query(None, description="Filter by specific account"),
    limit: int = Query(365, ge=1, le=1000, description="Maximum number of data points"),
) -> PortfolioHistoryResponse:
    """
    Get portfolio history for charting.

    Returns NAV history for the selected period.
    Uses FundShare records (backfilled historical NAV) as primary source,
    falls back to PortfolioSnapshot if available.
    """
    from app.models import FundShare

    start_date = _get_period_start_date(period)
    today = date.today()

    items: list[PortfolioHistoryItem] = []

    # First, try to get data from FundShare (backfilled historical NAV)
    # This is the preferred source as it has complete historical data
    if not account_id:  # FundShare is consolidated (no account breakdown)
        fund_shares_query = (
            select(FundShare)
            .where(FundShare.user_id == user.id)
            .where(FundShare.date >= start_date)
            .where(FundShare.date <= today)
            .order_by(FundShare.date.asc())
            .limit(limit)
        )

        fs_result = await db.execute(fund_shares_query)
        fund_shares = list(fs_result.scalars().all())

        if fund_shares:
            items = [
                PortfolioHistoryItem(
                    date=fs.date,
                    nav=fs.nav,
                    total_cost=Decimal("0"),  # Not tracked in FundShare
                    realized_pnl=Decimal("0"),  # Not tracked in FundShare
                    unrealized_pnl=Decimal("0"),  # Not tracked in FundShare
                    share_value=fs.share_value,
                    cumulative_return=fs.cumulative_return,
                )
                for fs in fund_shares
            ]

    # If no FundShare data, fall back to PortfolioSnapshot
    if not items:
        query = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == user.id)
            .where(PortfolioSnapshot.date >= start_date)
            .where(PortfolioSnapshot.date <= today)
            .order_by(PortfolioSnapshot.date.asc())
            .limit(limit)
        )

        if account_id:
            query = query.where(PortfolioSnapshot.account_id == account_id)
        else:
            query = query.where(PortfolioSnapshot.account_id.is_(None))

        result = await db.execute(query)
        snapshots = list(result.scalars().all())

        if snapshots:
            items = [
                PortfolioHistoryItem(
                    date=snap.date,
                    nav=snap.nav,
                    total_cost=snap.total_cost,
                    realized_pnl=snap.realized_pnl,
                    unrealized_pnl=snap.unrealized_pnl,
                )
                for snap in snapshots
            ]

    # Calculate period return
    period_return: Decimal | None = None
    start_nav: Decimal | None = None
    end_nav: Decimal | None = None

    if len(items) >= 2:
        start_nav = items[0].nav
        end_nav = items[-1].nav
        if start_nav > 0:
            period_return = (end_nav - start_nav) / start_nav

    return PortfolioHistoryResponse(
        items=items,
        total=len(items),
        period_return=period_return,
        start_nav=start_nav,
        end_nav=end_nav,
    )


# -------------------------------------------------------------------------
# Consolidated Portfolio Endpoint
# -------------------------------------------------------------------------


class ConsolidatedPositionItem(BaseModel):
    """Individual position in consolidated view."""

    ticker: str
    asset_name: str | None = None
    asset_type: AssetType
    currency: str
    quantity: Decimal
    avg_price: Decimal
    total_cost: Decimal
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    market_value_brl: Decimal | None = Field(None, description="Market value in BRL")
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    account_name: str | None = None


class AccountNAVItem(BaseModel):
    """NAV summary for a single account."""

    account_id: UUID
    account_name: str
    currency: str
    nav: Decimal = Field(..., description="NAV in account currency")
    nav_brl: Decimal = Field(..., description="NAV converted to BRL")
    ptax_rate: Decimal | None = Field(None, description="PTAX rate used for conversion")


class BreakdownItem(BaseModel):
    """Asset type breakdown."""

    category: str
    value: Decimal
    percentage: Decimal


class ConsolidatedPortfolioResponse(BaseModel):
    """Comprehensive consolidated portfolio response."""

    # Totals
    nav_total_brl: Decimal = Field(..., description="Total NAV in BRL")

    # By account breakdown
    nav_by_account: list[AccountNAVItem] = Field(
        default_factory=list,
        description="NAV breakdown by account",
    )

    # Positions
    positions: list[ConsolidatedPositionItem] = Field(
        default_factory=list,
        description="All positions with current prices",
    )

    # Breakdown by asset type
    breakdown: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Value breakdown by asset type",
    )

    # P&L
    realized_pnl_ytd: Decimal = Field(
        default=Decimal("0"),
        description="Realized P&L year-to-date",
    )
    total_unrealized_pnl: Decimal = Field(
        default=Decimal("0"),
        description="Total unrealized P&L",
    )

    # Exchange rate info
    ptax_date: date | None = Field(None, description="Date of PTAX rate used")
    ptax_rate: Decimal | None = Field(None, description="USD/BRL PTAX rate")

    # Metadata
    last_update: datetime | None = None
    positions_count: int = Field(default=0, description="Number of stock positions")
    fixed_income_count: int = Field(default=0, description="Number of fixed income positions")
    investment_funds_count: int = Field(default=0, description="Number of investment fund positions")
    derivatives_count: int = Field(default=0, description="Number of derivative positions")
    total_positions_count: int = Field(default=0, description="Total number of all positions")


@router.get("/consolidated", response_model=ConsolidatedPortfolioResponse)
async def get_consolidated_portfolio(
    user: AuthenticatedUser,
    db: DBSession,
) -> ConsolidatedPortfolioResponse:
    """
    Get fully consolidated portfolio view.

    Returns:
    - Total NAV in BRL (all accounts combined)
    - NAV per account (with currency conversion)
    - All positions with current prices and unrealized P&L
    - Breakdown by asset type
    - Year-to-date realized P&L
    - PTAX rate used for USD/BRL conversion
    """
    today = date.today()

    # Get exchange rate service for PTAX
    exchange_service = ExchangeRateService(db)
    ptax_result = await exchange_service.get_latest_ptax()
    ptax_date: date | None = None
    ptax_rate: Decimal | None = None

    if ptax_result:
        ptax_date, ptax_rate = ptax_result

    # Get all user accounts
    accounts_query = select(Account).where(Account.user_id == user.id).where(Account.is_active == True)
    accounts_result = await db.execute(accounts_query)
    accounts = {acc.id: acc for acc in accounts_result.scalars().all()}

    # Get all positions with asset data
    positions_query = (
        select(Position)
        .join(Position.account)
        .join(Position.asset)
        .options(selectinload(Position.asset), selectinload(Position.account))
        .where(Account.user_id == user.id)
        .where(Position.quantity > 0)
    )
    positions_result = await db.execute(positions_query)
    positions = list(positions_result.scalars().all())

    # Get fixed income positions
    fi_query = (
        select(FixedIncomePosition)
        .join(FixedIncomePosition.account)
        .options(selectinload(FixedIncomePosition.account))
        .where(Account.user_id == user.id)
        .where(
            (FixedIncomePosition.maturity_date >= today) |
            (FixedIncomePosition.maturity_date.is_(None))
        )
    )
    fi_result = await db.execute(fi_query)
    fixed_income_positions = list(fi_result.scalars().all())

    # Get investment fund positions
    fund_query = (
        select(InvestmentFundPosition)
        .join(InvestmentFundPosition.account)
        .options(selectinload(InvestmentFundPosition.account))
        .where(Account.user_id == user.id)
    )
    fund_result = await db.execute(fund_query)
    investment_fund_positions = list(fund_result.scalars().all())

    # Get latest snapshots per account for NAV values
    snapshot_subquery = (
        select(
            PortfolioSnapshot.account_id,
            func.max(PortfolioSnapshot.date).label("max_date"),
        )
        .where(PortfolioSnapshot.user_id == user.id)
        .where(PortfolioSnapshot.account_id.isnot(None))
        .group_by(PortfolioSnapshot.account_id)
        .subquery()
    )

    snapshots_query = (
        select(PortfolioSnapshot)
        .join(
            snapshot_subquery,
            (PortfolioSnapshot.account_id == snapshot_subquery.c.account_id) &
            (PortfolioSnapshot.date == snapshot_subquery.c.max_date)
        )
    )
    snapshots_result = await db.execute(snapshots_query)
    snapshots_by_account = {snap.account_id: snap for snap in snapshots_result.scalars().all()}

    # Get current prices for stock assets
    asset_ids = list(set(pos.asset_id for pos in positions))
    quote_service = QuoteService(db)
    current_prices = await quote_service.get_latest_prices(asset_ids) if asset_ids else {}

    # Build consolidated positions list
    consolidated_positions: list[ConsolidatedPositionItem] = []
    breakdown_by_type: dict[str, Decimal] = {}
    total_unrealized_pnl = Decimal("0")

    for pos in positions:
        asset = pos.asset
        account = pos.account
        currency = asset.currency or "BRL"

        # Get current price
        current_price = current_prices.get(pos.asset_id)

        # Calculate market value and unrealized P&L
        market_value: Decimal | None = None
        market_value_brl: Decimal | None = None
        unrealized_pnl: Decimal | None = None
        unrealized_pnl_pct: Decimal | None = None

        if current_price and current_price > 0:
            market_value = pos.quantity * current_price

            # Convert to BRL if needed
            if currency == "USD" and ptax_rate:
                market_value_brl = market_value * ptax_rate
            else:
                market_value_brl = market_value

            if pos.total_cost > 0:
                unrealized_pnl = market_value - pos.total_cost
                unrealized_pnl_pct = (unrealized_pnl / pos.total_cost) * 100
                total_unrealized_pnl += unrealized_pnl

        # Track breakdown by asset type
        asset_type_key = asset.asset_type.value if asset.asset_type else "other"
        breakdown_by_type[asset_type_key] = (
            breakdown_by_type.get(asset_type_key, Decimal("0"))
            + (market_value_brl or pos.total_cost)
        )

        consolidated_positions.append(ConsolidatedPositionItem(
            ticker=asset.ticker,
            asset_name=asset.name,
            asset_type=asset.asset_type,
            currency=currency,
            quantity=pos.quantity,
            avg_price=pos.avg_price,
            total_cost=pos.total_cost,
            current_price=current_price,
            market_value=market_value,
            market_value_brl=market_value_brl,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            account_name=account.name if account else None,
        ))

    # Add fixed income to breakdown
    fi_total = sum(fi.total_value for fi in fixed_income_positions)
    if fi_total > 0:
        breakdown_by_type["renda_fixa"] = breakdown_by_type.get("renda_fixa", Decimal("0")) + fi_total

    # Add investment funds to breakdown
    fund_total = sum(
        f.net_balance if f.net_balance is not None else f.gross_balance
        for f in investment_fund_positions
    )
    if fund_total > 0:
        breakdown_by_type["fundos_investimento"] = (
            breakdown_by_type.get("fundos_investimento", Decimal("0")) + fund_total
        )

    # Build NAV by account using snapshots
    nav_by_account: list[AccountNAVItem] = []
    nav_total_brl = Decimal("0")

    for account_id, account in accounts.items():
        snapshot = snapshots_by_account.get(account_id)

        if snapshot and snapshot.nav > 0:
            nav = snapshot.nav
        else:
            # Fall back to calculated value
            account_positions_value = sum(
                (p.market_value_brl or p.total_cost)
                for p in consolidated_positions
                if p.account_name == account.name
            )
            account_fi_value = sum(
                fi.total_value for fi in fixed_income_positions
                if fi.account_id == account_id
            )
            account_fund_value = sum(
                f.net_balance if f.net_balance is not None else f.gross_balance
                for f in investment_fund_positions
                if f.account_id == account_id
            )
            nav = account_positions_value + account_fi_value + account_fund_value

        # Convert to BRL if needed
        account_currency = account.currency or "BRL"
        if account_currency == "USD" and ptax_rate:
            nav_brl = nav * ptax_rate
            used_ptax = ptax_rate
        else:
            nav_brl = nav
            used_ptax = None

        nav_total_brl += nav_brl

        if nav > 0:  # Only include accounts with value
            nav_by_account.append(AccountNAVItem(
                account_id=account_id,
                account_name=account.name,
                currency=account_currency,
                nav=nav,
                nav_brl=nav_brl,
                ptax_rate=used_ptax,
            ))

    # Get realized P&L YTD
    pnl_service = PnLService(db)
    ytd_start = today.replace(month=1, day=1)
    realized_summary = await pnl_service.calculate_realized_pnl(
        user_id=user.id,
        start_date=ytd_start,
        end_date=today,
    )

    # Sort positions by market value descending
    consolidated_positions.sort(
        key=lambda p: p.market_value_brl or p.total_cost,
        reverse=True,
    )

    return ConsolidatedPortfolioResponse(
        nav_total_brl=nav_total_brl,
        nav_by_account=nav_by_account,
        positions=consolidated_positions,
        breakdown=breakdown_by_type,
        realized_pnl_ytd=realized_summary.total_realized_pnl,
        total_unrealized_pnl=total_unrealized_pnl,
        ptax_date=ptax_date,
        ptax_rate=ptax_rate,
        last_update=datetime.utcnow(),
        positions_count=len(consolidated_positions),
        fixed_income_count=len(fixed_income_positions),
        investment_funds_count=len(investment_fund_positions),
        derivatives_count=0,  # TODO: count derivatives when implemented
        total_positions_count=(
            len(consolidated_positions) +
            len(fixed_income_positions) +
            len(investment_fund_positions)
        ),
    )
