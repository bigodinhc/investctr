"""
NAV (Net Asset Value) service for the quota system.

Calculates NAV, issues and redeems shares based on cash flows.
Implements the fund share management system for personal portfolios.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Account, CashFlow, FundShare
from app.schemas.enums import CashFlowType, PositionType
from app.services.position_service import PositionService
from app.services.quote_service import QuoteService
from app.services.exchange_rate_service import ExchangeRateService

logger = get_logger(__name__)

# Initial share value when starting the fund
INITIAL_SHARE_VALUE = Decimal("100.00000000")


@dataclass
class NAVResult:
    """Result of NAV calculation."""

    user_id: UUID
    date: date
    total_market_value: Decimal
    total_cash: Decimal
    nav: Decimal
    positions_count: int
    positions_with_prices: int
    # BRL-converted values (optional, for multi-currency support)
    total_market_value_brl: Decimal | None = None
    total_cash_brl: Decimal | None = None
    nav_brl: Decimal | None = None
    ptax_rate: Decimal | None = None  # USD/BRL rate used


@dataclass
class SharesResult:
    """Result of share issuance or redemption."""

    cash_flow_id: UUID
    amount: Decimal
    share_value: Decimal
    shares_affected: Decimal
    new_shares_outstanding: Decimal


@dataclass
class FundPerformance:
    """Fund performance metrics."""

    current_nav: Decimal
    current_share_value: Decimal
    shares_outstanding: Decimal
    total_return: Decimal | None  # Cumulative return
    daily_return: Decimal | None
    mtd_return: Decimal | None  # Month-to-date
    ytd_return: Decimal | None  # Year-to-date
    one_year_return: Decimal | None
    max_drawdown: Decimal | None
    volatility: Decimal | None  # Annualized volatility


class NAVService:
    """Service for NAV calculation and share management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_nav(
        self,
        user_id: UUID,
        target_date: date | None = None,
        convert_to_brl: bool = True,
    ) -> NAVResult:
        """
        Calculate Net Asset Value for a user's portfolio.

        RN-01: NAV = Σ(positions × current_price) + cash_balance

        Multi-currency support:
        - Positions in USD are converted to BRL using PTAX rate
        - Cash in USD is converted to BRL using PTAX rate
        - NAV is returned in both original currency and BRL

        Args:
            user_id: User UUID
            target_date: Date for NAV calculation (defaults to today)
            convert_to_brl: Whether to convert USD values to BRL (default True)

        Returns:
            NAVResult with NAV components and totals (including BRL values)
        """
        if target_date is None:
            target_date = date.today()

        logger.info(
            "nav_calculation_start",
            user_id=str(user_id),
            date=target_date.isoformat(),
        )

        # Get PTAX rate for currency conversion
        ptax_rate: Decimal | None = None
        if convert_to_brl:
            exchange_service = ExchangeRateService(self.db)
            ptax_rate = await exchange_service.get_ptax(target_date)

        # 1. Get all positions for user
        position_service = PositionService(self.db)
        positions = await position_service.get_positions_with_assets(user_id=user_id)

        # 2. Get current prices for all assets
        asset_ids = [pos.asset_id for pos in positions if pos.quantity > 0]
        quote_service = QuoteService(self.db)
        current_prices = await quote_service.get_prices_at_date(asset_ids, target_date)

        # 3. Calculate market value per position
        # For Long/Short portfolios: NAV = Long_Value - Short_Value + Cash
        total_market_value = Decimal("0")
        total_market_value_brl = Decimal("0")
        long_value = Decimal("0")
        short_value = Decimal("0")
        positions_with_prices = 0

        for pos in positions:
            if pos.quantity <= 0:
                continue

            position_type = getattr(pos, "position_type", PositionType.LONG)
            price = current_prices.get(pos.asset_id)

            if price is not None:
                market_value = pos.quantity * price
                positions_with_prices += 1
            else:
                # Use cost basis if no price available
                market_value = pos.total_cost

            # Get asset currency for conversion
            asset_currency = getattr(pos.asset, "currency", "BRL") if pos.asset else "BRL"
            if asset_currency == "USD" and ptax_rate:
                market_value_brl = market_value * ptax_rate
            else:
                market_value_brl = market_value

            # SHORT positions reduce NAV (liability to buy back)
            # LONG positions increase NAV (asset value)
            if position_type == PositionType.SHORT:
                short_value += market_value
                total_market_value -= market_value
                total_market_value_brl -= market_value_brl
            else:
                long_value += market_value
                total_market_value += market_value
                total_market_value_brl += market_value_brl

        # 4. Get cash balance from CashFlow aggregation
        total_cash = await self._get_cash_balance(user_id, target_date)

        # Cash flows already have exchange_rate applied for currency conversion
        # The _get_cash_balance already multiplies by exchange_rate
        total_cash_brl = total_cash

        # 5. Calculate NAV
        nav = total_market_value + total_cash
        nav_brl = total_market_value_brl + total_cash_brl

        logger.info(
            "nav_calculation_complete",
            user_id=str(user_id),
            date=target_date.isoformat(),
            nav=str(nav),
            nav_brl=str(nav_brl),
            market_value=str(total_market_value),
            market_value_brl=str(total_market_value_brl),
            long_value=str(long_value),
            short_value=str(short_value),
            cash=str(total_cash),
            positions=len(positions),
            positions_with_prices=positions_with_prices,
            ptax_rate=str(ptax_rate) if ptax_rate else None,
        )

        return NAVResult(
            user_id=user_id,
            date=target_date,
            total_market_value=total_market_value,
            total_cash=total_cash,
            nav=nav,
            positions_count=len([p for p in positions if p.quantity > 0]),
            positions_with_prices=positions_with_prices,
            total_market_value_brl=total_market_value_brl,
            total_cash_brl=total_cash_brl,
            nav_brl=nav_brl,
            ptax_rate=ptax_rate,
        )

    async def _get_cash_balance(
        self,
        user_id: UUID,
        as_of_date: date | None = None,
    ) -> Decimal:
        """
        Calculate cash balance from cash flows.

        Deposits add to balance, withdrawals subtract.

        Args:
            user_id: User UUID
            as_of_date: Calculate balance as of this date

        Returns:
            Net cash balance
        """
        query = (
            select(
                CashFlow.type,
                func.sum(CashFlow.amount * CashFlow.exchange_rate).label("total"),
            )
            .join(Account, CashFlow.account_id == Account.id)
            .where(Account.user_id == user_id)
            .group_by(CashFlow.type)
        )

        if as_of_date:
            end_of_day = datetime.combine(as_of_date, datetime.max.time())
            query = query.where(CashFlow.executed_at <= end_of_day)

        result = await self.db.execute(query)
        rows = result.fetchall()

        balance = Decimal("0")
        for row in rows:
            if row.type == CashFlowType.DEPOSIT:
                balance += row.total or Decimal("0")
            elif row.type == CashFlowType.WITHDRAWAL:
                balance -= row.total or Decimal("0")

        return balance

    async def get_previous_share_value(
        self,
        user_id: UUID,
        before_date: date,
    ) -> Decimal:
        """
        Get the share value from the previous day.

        If no previous record exists, returns initial share value.

        Args:
            user_id: User UUID
            before_date: Get value before this date

        Returns:
            Share value from D-1, or INITIAL_SHARE_VALUE if first day
        """
        query = (
            select(FundShare)
            .where(
                and_(
                    FundShare.user_id == user_id,
                    FundShare.date < before_date,
                )
            )
            .order_by(FundShare.date.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        previous = result.scalar_one_or_none()

        if previous is None:
            return INITIAL_SHARE_VALUE

        return previous.share_value

    async def get_current_shares_outstanding(
        self,
        user_id: UUID,
    ) -> Decimal:
        """
        Get the current total shares outstanding.

        Args:
            user_id: User UUID

        Returns:
            Total shares outstanding, or 0 if none
        """
        query = (
            select(FundShare)
            .where(FundShare.user_id == user_id)
            .order_by(FundShare.date.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        latest = result.scalar_one_or_none()

        if latest is None:
            return Decimal("0")

        return latest.shares_outstanding

    async def issue_shares(
        self,
        user_id: UUID,
        cash_flow_id: UUID,
        amount: Decimal,
        executed_date: date,
    ) -> SharesResult:
        """
        Issue new shares for a deposit.

        RN-03: Cotas Emitidas = Valor Aporte / Valor Cota (D-1)

        Args:
            user_id: User UUID
            cash_flow_id: CashFlow record ID
            amount: Deposit amount in BRL
            executed_date: Date of the deposit

        Returns:
            SharesResult with new shares issued
        """
        logger.info(
            "issue_shares_start",
            user_id=str(user_id),
            cash_flow_id=str(cash_flow_id),
            amount=str(amount),
            date=executed_date.isoformat(),
        )

        # Get previous day's share value
        share_value = await self.get_previous_share_value(user_id, executed_date)

        # Calculate new shares
        new_shares = amount / share_value

        # Get current shares outstanding
        current_shares = await self.get_current_shares_outstanding(user_id)
        new_shares_outstanding = current_shares + new_shares

        # Update the CashFlow record with shares_affected
        query = select(CashFlow).where(CashFlow.id == cash_flow_id)
        result = await self.db.execute(query)
        cash_flow = result.scalar_one_or_none()

        if cash_flow:
            cash_flow.shares_affected = new_shares
            await self.db.flush()

        logger.info(
            "issue_shares_complete",
            user_id=str(user_id),
            new_shares=str(new_shares),
            share_value=str(share_value),
            new_outstanding=str(new_shares_outstanding),
        )

        return SharesResult(
            cash_flow_id=cash_flow_id,
            amount=amount,
            share_value=share_value,
            shares_affected=new_shares,
            new_shares_outstanding=new_shares_outstanding,
        )

    async def redeem_shares(
        self,
        user_id: UUID,
        cash_flow_id: UUID,
        amount: Decimal,
        executed_date: date,
    ) -> SharesResult:
        """
        Redeem shares for a withdrawal.

        RN-04: Similar to issue_shares but for withdrawals.
        Validates user has enough shares.

        Args:
            user_id: User UUID
            cash_flow_id: CashFlow record ID
            amount: Withdrawal amount in BRL
            executed_date: Date of the withdrawal

        Returns:
            SharesResult with shares redeemed

        Raises:
            ValueError: If insufficient shares
        """
        logger.info(
            "redeem_shares_start",
            user_id=str(user_id),
            cash_flow_id=str(cash_flow_id),
            amount=str(amount),
            date=executed_date.isoformat(),
        )

        # Get previous day's share value
        share_value = await self.get_previous_share_value(user_id, executed_date)

        # Calculate shares to redeem
        shares_to_redeem = amount / share_value

        # Get current shares outstanding
        current_shares = await self.get_current_shares_outstanding(user_id)

        if shares_to_redeem > current_shares:
            raise ValueError(
                f"Insufficient shares: need {shares_to_redeem}, have {current_shares}"
            )

        new_shares_outstanding = current_shares - shares_to_redeem

        # Update the CashFlow record with shares_affected (negative for redemption)
        query = select(CashFlow).where(CashFlow.id == cash_flow_id)
        result = await self.db.execute(query)
        cash_flow = result.scalar_one_or_none()

        if cash_flow:
            cash_flow.shares_affected = -shares_to_redeem
            await self.db.flush()

        logger.info(
            "redeem_shares_complete",
            user_id=str(user_id),
            shares_redeemed=str(shares_to_redeem),
            share_value=str(share_value),
            new_outstanding=str(new_shares_outstanding),
        )

        return SharesResult(
            cash_flow_id=cash_flow_id,
            amount=amount,
            share_value=share_value,
            shares_affected=-shares_to_redeem,
            new_shares_outstanding=new_shares_outstanding,
        )

    async def create_daily_fund_share(
        self,
        user_id: UUID,
        target_date: date | None = None,
    ) -> FundShare | None:
        """
        Create or update the daily FundShare record.

        Calculates NAV, share value, and returns for the day.

        Args:
            user_id: User UUID
            target_date: Date for the record (defaults to today)

        Returns:
            Created/updated FundShare record, or None if no positions
        """
        if target_date is None:
            target_date = date.today()

        logger.info(
            "create_daily_fund_share_start",
            user_id=str(user_id),
            date=target_date.isoformat(),
        )

        # Calculate NAV for the date
        nav_result = await self.calculate_nav(user_id, target_date)

        if nav_result.nav == 0:
            logger.info(
                "create_daily_fund_share_skip_zero_nav",
                user_id=str(user_id),
                date=target_date.isoformat(),
            )
            return None

        # Get shares outstanding (sum of all shares_affected from cash flows)
        shares_outstanding = await self._calculate_shares_outstanding(
            user_id, target_date
        )

        if shares_outstanding <= 0:
            # If no shares yet, this is initial investment
            # Use initial share value
            shares_outstanding = nav_result.nav / INITIAL_SHARE_VALUE

        # Calculate share value
        share_value = nav_result.nav / shares_outstanding

        # Get previous day's fund share for return calculation
        previous = await self._get_previous_fund_share(user_id, target_date)

        daily_return: Decimal | None = None
        cumulative_return: Decimal | None = None

        if previous:
            daily_return = (share_value - previous.share_value) / previous.share_value
            # Cumulative return from initial value
            cumulative_return = (
                share_value - INITIAL_SHARE_VALUE
            ) / INITIAL_SHARE_VALUE
        else:
            cumulative_return = (
                share_value - INITIAL_SHARE_VALUE
            ) / INITIAL_SHARE_VALUE

        # Upsert the FundShare record
        fund_share = await self._upsert_fund_share(
            user_id=user_id,
            target_date=target_date,
            nav=nav_result.nav,
            shares_outstanding=shares_outstanding,
            share_value=share_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
        )

        logger.info(
            "create_daily_fund_share_complete",
            user_id=str(user_id),
            date=target_date.isoformat(),
            nav=str(nav_result.nav),
            share_value=str(share_value),
            daily_return=str(daily_return) if daily_return else None,
        )

        return fund_share

    async def _calculate_shares_outstanding(
        self,
        user_id: UUID,
        as_of_date: date,
    ) -> Decimal:
        """
        Calculate total shares outstanding from cash flow history.

        Args:
            user_id: User UUID
            as_of_date: Calculate as of this date

        Returns:
            Total shares outstanding
        """
        end_of_day = datetime.combine(as_of_date, datetime.max.time())

        query = (
            select(func.sum(CashFlow.shares_affected))
            .join(Account, CashFlow.account_id == Account.id)
            .where(
                and_(
                    Account.user_id == user_id,
                    CashFlow.executed_at <= end_of_day,
                    CashFlow.shares_affected.isnot(None),
                )
            )
        )

        result = await self.db.execute(query)
        total = result.scalar_one_or_none()

        return total or Decimal("0")

    async def _get_previous_fund_share(
        self,
        user_id: UUID,
        before_date: date,
    ) -> FundShare | None:
        """Get the most recent FundShare before the given date."""
        query = (
            select(FundShare)
            .where(
                and_(
                    FundShare.user_id == user_id,
                    FundShare.date < before_date,
                )
            )
            .order_by(FundShare.date.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _upsert_fund_share(
        self,
        user_id: UUID,
        target_date: date,
        nav: Decimal,
        shares_outstanding: Decimal,
        share_value: Decimal,
        daily_return: Decimal | None,
        cumulative_return: Decimal | None,
    ) -> FundShare:
        """Insert or update a FundShare record."""
        # Check if record exists
        query = select(FundShare).where(
            and_(
                FundShare.user_id == user_id,
                FundShare.date == target_date,
            )
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            existing.nav = nav
            existing.shares_outstanding = shares_outstanding
            existing.share_value = share_value
            existing.daily_return = daily_return
            existing.cumulative_return = cumulative_return
            await self.db.flush()
            return existing
        else:
            fund_share = FundShare(
                user_id=user_id,
                date=target_date,
                nav=nav,
                shares_outstanding=shares_outstanding,
                share_value=share_value,
                daily_return=daily_return,
                cumulative_return=cumulative_return,
            )
            self.db.add(fund_share)
            await self.db.flush()
            return fund_share

    async def get_fund_shares_history(
        self,
        user_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 365,
    ) -> list[FundShare]:
        """
        Get FundShare history for a user.

        Args:
            user_id: User UUID
            start_date: Start date filter (inclusive)
            end_date: End date filter (inclusive)
            limit: Maximum number of records

        Returns:
            List of FundShare records ordered by date descending
        """
        query = (
            select(FundShare)
            .where(FundShare.user_id == user_id)
            .order_by(FundShare.date.desc())
            .limit(limit)
        )

        if start_date:
            query = query.where(FundShare.date >= start_date)
        if end_date:
            query = query.where(FundShare.date <= end_date)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_fund_share(
        self,
        user_id: UUID,
    ) -> FundShare | None:
        """Get the most recent FundShare record for a user."""
        query = (
            select(FundShare)
            .where(FundShare.user_id == user_id)
            .order_by(FundShare.date.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_fund_performance(
        self,
        user_id: UUID,
    ) -> FundPerformance | None:
        """
        Calculate comprehensive fund performance metrics.

        Args:
            user_id: User UUID

        Returns:
            FundPerformance with all metrics, or None if no data
        """
        # Get latest fund share
        latest = await self.get_latest_fund_share(user_id)
        if not latest:
            return None

        today = date.today()
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)
        one_year_ago = today - timedelta(days=365)

        # Get MTD start value
        mtd_start = await self._get_fund_share_at_date(
            user_id, start_of_month - timedelta(days=1)
        )
        mtd_return: Decimal | None = None
        if mtd_start and mtd_start.share_value > 0:
            mtd_return = (
                latest.share_value - mtd_start.share_value
            ) / mtd_start.share_value

        # Get YTD start value
        ytd_start = await self._get_fund_share_at_date(
            user_id, start_of_year - timedelta(days=1)
        )
        ytd_return: Decimal | None = None
        if ytd_start and ytd_start.share_value > 0:
            ytd_return = (
                latest.share_value - ytd_start.share_value
            ) / ytd_start.share_value

        # Get 1Y return
        one_year_start = await self._get_fund_share_at_date(user_id, one_year_ago)
        one_year_return: Decimal | None = None
        if one_year_start and one_year_start.share_value > 0:
            one_year_return = (
                latest.share_value - one_year_start.share_value
            ) / one_year_start.share_value

        # Calculate max drawdown and volatility (last 252 trading days)
        history = await self.get_fund_shares_history(user_id, limit=252)
        max_drawdown = self._calculate_max_drawdown(history)
        volatility = self._calculate_volatility(history)

        return FundPerformance(
            current_nav=latest.nav,
            current_share_value=latest.share_value,
            shares_outstanding=latest.shares_outstanding,
            total_return=latest.cumulative_return,
            daily_return=latest.daily_return,
            mtd_return=mtd_return,
            ytd_return=ytd_return,
            one_year_return=one_year_return,
            max_drawdown=max_drawdown,
            volatility=volatility,
        )

    async def _get_fund_share_at_date(
        self,
        user_id: UUID,
        target_date: date,
    ) -> FundShare | None:
        """Get fund share on or before target date."""
        query = (
            select(FundShare)
            .where(
                and_(
                    FundShare.user_id == user_id,
                    FundShare.date <= target_date,
                )
            )
            .order_by(FundShare.date.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _calculate_max_drawdown(
        self,
        history: list[FundShare],
    ) -> Decimal | None:
        """Calculate maximum drawdown from peak."""
        if len(history) < 2:
            return None

        # Reverse to oldest first
        sorted_history = sorted(history, key=lambda x: x.date)

        peak = Decimal("0")
        max_dd = Decimal("0")

        for fs in sorted_history:
            if fs.share_value > peak:
                peak = fs.share_value

            if peak > 0:
                drawdown = (peak - fs.share_value) / peak
                if drawdown > max_dd:
                    max_dd = drawdown

        return max_dd if max_dd > 0 else None

    def _calculate_volatility(
        self,
        history: list[FundShare],
    ) -> Decimal | None:
        """Calculate annualized volatility from daily returns."""
        if len(history) < 20:
            return None

        # Get daily returns
        returns = [
            float(fs.daily_return) for fs in history if fs.daily_return is not None
        ]

        if len(returns) < 20:
            return None

        # Calculate standard deviation
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        std_dev = variance**0.5

        # Annualize (252 trading days)
        annualized = std_dev * (252**0.5)

        return Decimal(str(round(annualized, 6)))


# Utility functions
async def calculate_nav(
    db: AsyncSession,
    user_id: UUID,
    target_date: date | None = None,
) -> NAVResult:
    """Utility function to calculate NAV."""
    service = NAVService(db)
    return await service.calculate_nav(user_id, target_date)


async def create_daily_fund_share(
    db: AsyncSession,
    user_id: UUID,
    target_date: date | None = None,
) -> FundShare | None:
    """Utility function to create daily fund share."""
    service = NAVService(db)
    return await service.create_daily_fund_share(user_id, target_date)
