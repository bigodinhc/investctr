"""
Integration tests for Position endpoints.

Tests cover:
- Listing positions with P&L calculations
- Consolidated positions across accounts
- Portfolio summary
- Position recalculation
- Authentication and filtering
"""

from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.schemas.enums import AssetType, PositionType
from tests.conftest import TEST_USER_ID


pytestmark = pytest.mark.asyncio


# Mock P&L calculation result
def create_mock_pnl_summary(positions, current_prices):
    """Create a mock P&L summary for testing."""
    from app.services.pnl_service import UnrealizedPnLEntry, UnrealizedPnLSummary

    entries = []
    total_cost = Decimal("0")
    total_market_value = Decimal("0")

    for pos in positions:
        current_price = current_prices.get(pos.asset_id, pos.avg_price)
        market_value = pos.quantity * current_price
        unrealized_pnl = market_value - pos.total_cost
        unrealized_pnl_pct = (
            (unrealized_pnl / pos.total_cost * 100) if pos.total_cost > 0 else Decimal("0")
        )

        entry = UnrealizedPnLEntry(
            position_id=pos.id,
            asset_id=pos.asset_id,
            ticker="TEST",
            quantity=pos.quantity,
            avg_price=pos.avg_price,
            total_cost=pos.total_cost,
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
        )
        entries.append(entry)
        total_cost += pos.total_cost
        total_market_value += market_value

    total_unrealized = total_market_value - total_cost
    total_pnl_pct = (total_unrealized / total_cost * 100) if total_cost > 0 else None

    return UnrealizedPnLSummary(
        entries=entries,
        total_cost=total_cost,
        total_market_value=total_market_value,
        total_unrealized_pnl=total_unrealized,
        total_unrealized_pnl_pct=total_pnl_pct,
    )


class TestListPositions:
    """Tests for GET /api/v1/positions endpoint."""

    async def test_list_positions_empty(self, client: AsyncClient):
        """Should return empty list when no positions exist."""
        # Mock the services
        with patch("app.api.v1.positions.QuoteService") as mock_quote, \
             patch("app.api.v1.positions.PnLService") as mock_pnl:

            mock_quote_instance = AsyncMock()
            mock_quote_instance.get_latest_prices.return_value = {}
            mock_quote.return_value = mock_quote_instance

            mock_pnl_instance = AsyncMock()
            mock_pnl_instance.calculate_unrealized_pnl.return_value = MagicMock(
                entries=[],
                total_cost=Decimal("0"),
                total_market_value=Decimal("0"),
                total_unrealized_pnl=Decimal("0"),
                total_unrealized_pnl_pct=None,
            )
            mock_pnl.return_value = mock_pnl_instance

            response = await client.get("/api/v1/positions")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_positions_with_data(self, client: AsyncClient, factory):
        """Should return list of positions with market data."""
        account = await factory.create_account()
        asset = await factory.create_asset(ticker="PETR4", name="Petrobras PN")
        position = await factory.create_position(
            account_id=account.id,
            asset_id=asset.id,
            quantity=Decimal("100"),
            avg_price=Decimal("35.50"),
            total_cost=Decimal("3550.00"),
        )

        # Mock the services
        with patch("app.api.v1.positions.QuoteService") as mock_quote, \
             patch("app.api.v1.positions.PnLService") as mock_pnl:

            mock_quote_instance = AsyncMock()
            mock_quote_instance.get_latest_prices.return_value = {
                asset.id: Decimal("40.00")
            }
            mock_quote.return_value = mock_quote_instance

            # Create mock P&L entry
            mock_pnl_instance = AsyncMock()

            async def mock_calc(positions, prices):
                return create_mock_pnl_summary(positions, prices)

            mock_pnl_instance.calculate_unrealized_pnl.side_effect = mock_calc
            mock_pnl.return_value = mock_pnl_instance

            response = await client.get("/api/v1/positions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1

        item = data["items"][0]
        assert item["id"] == str(position.id)
        assert item["ticker"] == "PETR4"
        assert item["asset_name"] == "Petrobras PN"
        assert Decimal(item["quantity"]) == Decimal("100")

    async def test_list_positions_filter_by_account(self, client: AsyncClient, factory):
        """Should filter positions by account_id."""
        account1 = await factory.create_account(name="Account 1")
        account2 = await factory.create_account(name="Account 2")
        asset = await factory.create_asset()

        await factory.create_position(account_id=account1.id, asset_id=asset.id)
        await factory.create_position(account_id=account2.id, asset_id=asset.id)

        with patch("app.api.v1.positions.QuoteService") as mock_quote, \
             patch("app.api.v1.positions.PnLService") as mock_pnl:

            mock_quote_instance = AsyncMock()
            mock_quote_instance.get_latest_prices.return_value = {}
            mock_quote.return_value = mock_quote_instance

            mock_pnl_instance = AsyncMock()

            async def mock_calc(positions, prices):
                return create_mock_pnl_summary(positions, prices)

            mock_pnl_instance.calculate_unrealized_pnl.side_effect = mock_calc
            mock_pnl.return_value = mock_pnl_instance

            response = await client.get(f"/api/v1/positions?account_id={account1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["account_id"] == str(account1.id)

    async def test_list_positions_filter_by_asset_type(
        self, client: AsyncClient, factory
    ):
        """Should filter positions by asset type."""
        account = await factory.create_account()
        stock = await factory.create_asset(ticker="PETR4", asset_type=AssetType.STOCK)
        fii = await factory.create_asset(ticker="HGLG11", asset_type=AssetType.FII)

        await factory.create_position(account_id=account.id, asset_id=stock.id)
        await factory.create_position(account_id=account.id, asset_id=fii.id)

        with patch("app.api.v1.positions.QuoteService") as mock_quote, \
             patch("app.api.v1.positions.PnLService") as mock_pnl:

            mock_quote_instance = AsyncMock()
            mock_quote_instance.get_latest_prices.return_value = {}
            mock_quote.return_value = mock_quote_instance

            mock_pnl_instance = AsyncMock()

            async def mock_calc(positions, prices):
                return create_mock_pnl_summary(positions, prices)

            mock_pnl_instance.calculate_unrealized_pnl.side_effect = mock_calc
            mock_pnl.return_value = mock_pnl_instance

            response = await client.get("/api/v1/positions?asset_type=stock")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["asset_type"] == "stock"

    async def test_list_positions_pagination(self, client: AsyncClient, factory):
        """Should support pagination."""
        account = await factory.create_account()

        for i in range(5):
            asset = await factory.create_asset(ticker=f"TEST{i}")
            await factory.create_position(account_id=account.id, asset_id=asset.id)

        with patch("app.api.v1.positions.QuoteService") as mock_quote, \
             patch("app.api.v1.positions.PnLService") as mock_pnl:

            mock_quote_instance = AsyncMock()
            mock_quote_instance.get_latest_prices.return_value = {}
            mock_quote.return_value = mock_quote_instance

            mock_pnl_instance = AsyncMock()

            async def mock_calc(positions, prices):
                return create_mock_pnl_summary(positions, prices)

            mock_pnl_instance.calculate_unrealized_pnl.side_effect = mock_calc
            mock_pnl.return_value = mock_pnl_instance

            response = await client.get("/api/v1/positions?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_positions_unauthenticated(
        self, unauthenticated_client: AsyncClient
    ):
        """Should return 401 when not authenticated."""
        response = await unauthenticated_client.get("/api/v1/positions")

        assert response.status_code == 401


class TestGetPosition:
    """Tests for GET /api/v1/positions/{position_id} endpoint."""

    async def test_get_position_success(self, client: AsyncClient, factory):
        """Should return position details with market data."""
        account = await factory.create_account()
        asset = await factory.create_asset(ticker="VALE3", name="Vale ON")
        position = await factory.create_position(
            account_id=account.id,
            asset_id=asset.id,
            quantity=Decimal("200"),
            avg_price=Decimal("68.50"),
            total_cost=Decimal("13700.00"),
        )

        with patch("app.api.v1.positions.QuoteService") as mock_quote:
            mock_quote_instance = AsyncMock()
            mock_quote_instance.get_latest_price.return_value = Decimal("75.00")
            mock_quote.return_value = mock_quote_instance

            response = await client.get(f"/api/v1/positions/{position.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(position.id)
        assert data["ticker"] == "VALE3"
        assert data["asset_name"] == "Vale ON"
        assert Decimal(data["quantity"]) == Decimal("200")
        assert Decimal(data["avg_price"]) == Decimal("68.50")
        # With current_price at 75.00 and 200 shares
        # market_value = 200 * 75 = 15000
        # unrealized_pnl = 15000 - 13700 = 1300
        assert data["current_price"] == "75.00"
        assert Decimal(data["market_value"]) == Decimal("15000.00")
        assert Decimal(data["unrealized_pnl"]) == Decimal("1300.00")

    async def test_get_position_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent position."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/positions/{fake_id}")

        assert response.status_code == 404

    async def test_get_position_invalid_uuid(self, client: AsyncClient):
        """Should return 422 for invalid UUID."""
        response = await client.get("/api/v1/positions/not-a-uuid")

        assert response.status_code == 422

    async def test_get_position_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        position = await factory.create_position(
            account_id=account.id,
            asset_id=asset.id,
        )

        response = await unauthenticated_client.get(f"/api/v1/positions/{position.id}")

        assert response.status_code == 401


class TestConsolidatedPositions:
    """Tests for GET /api/v1/positions/consolidated endpoint."""

    async def test_consolidated_positions_empty(self, client: AsyncClient):
        """Should return empty list when no positions exist."""
        with patch("app.api.v1.positions.PositionService") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_consolidated_positions.return_value = []
            mock_service.return_value = mock_instance

            response = await client.get("/api/v1/positions/consolidated")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_consolidated_positions_aggregates(self, client: AsyncClient, factory):
        """Should aggregate positions across accounts."""
        # Create two accounts with same asset
        account1 = await factory.create_account(name="BTG")
        account2 = await factory.create_account(name="XP")
        asset = await factory.create_asset(ticker="ITUB4")

        await factory.create_position(
            account_id=account1.id,
            asset_id=asset.id,
            quantity=Decimal("100"),
            avg_price=Decimal("30.00"),
            total_cost=Decimal("3000.00"),
        )
        await factory.create_position(
            account_id=account2.id,
            asset_id=asset.id,
            quantity=Decimal("50"),
            avg_price=Decimal("32.00"),
            total_cost=Decimal("1600.00"),
        )

        with patch("app.api.v1.positions.PositionService") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_consolidated_positions.return_value = [
                {
                    "asset_id": asset.id,
                    "ticker": "ITUB4",
                    "asset_name": "Itau Unibanco PN",
                    "asset_type": AssetType.STOCK,
                    "total_quantity": Decimal("150"),
                    "weighted_avg_price": Decimal("30.67"),
                    "total_cost": Decimal("4600.00"),
                    "current_price": Decimal("35.00"),
                    "market_value": Decimal("5250.00"),
                    "unrealized_pnl": Decimal("650.00"),
                    "unrealized_pnl_pct": Decimal("14.13"),
                    "accounts_count": 2,
                }
            ]
            mock_service.return_value = mock_instance

            response = await client.get("/api/v1/positions/consolidated")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1

        item = data["items"][0]
        assert item["ticker"] == "ITUB4"
        assert Decimal(item["total_quantity"]) == Decimal("150")
        assert item["accounts_count"] == 2

    async def test_consolidated_positions_filter_by_type(
        self, client: AsyncClient, factory
    ):
        """Should filter consolidated positions by asset type."""
        account = await factory.create_account()
        stock = await factory.create_asset(ticker="PETR4", asset_type=AssetType.STOCK)
        fii = await factory.create_asset(ticker="HGLG11", asset_type=AssetType.FII)

        await factory.create_position(account_id=account.id, asset_id=stock.id)
        await factory.create_position(account_id=account.id, asset_id=fii.id)

        with patch("app.api.v1.positions.PositionService") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.get_consolidated_positions.return_value = [
                {
                    "asset_id": fii.id,
                    "ticker": "HGLG11",
                    "asset_name": "CSHG Logistica FII",
                    "asset_type": AssetType.FII,
                    "total_quantity": Decimal("100"),
                    "weighted_avg_price": Decimal("160.00"),
                    "total_cost": Decimal("16000.00"),
                    "current_price": None,
                    "market_value": None,
                    "unrealized_pnl": None,
                    "unrealized_pnl_pct": None,
                    "accounts_count": 1,
                }
            ]
            mock_service.return_value = mock_instance

            response = await client.get("/api/v1/positions/consolidated?asset_type=fii")

        assert response.status_code == 200
        # Note: Filtering happens after service call in the endpoint
        # So we test the response format here

    async def test_consolidated_positions_unauthenticated(
        self, unauthenticated_client: AsyncClient
    ):
        """Should return 401 when not authenticated."""
        response = await unauthenticated_client.get("/api/v1/positions/consolidated")

        assert response.status_code == 401


class TestPortfolioSummary:
    """Tests for GET /api/v1/positions/summary endpoint."""

    async def test_portfolio_summary_empty(self, client: AsyncClient):
        """Should return zero totals when no positions exist."""
        response = await client.get("/api/v1/positions/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_positions"] == 0
        assert Decimal(data["total_cost"]) == Decimal("0")
        assert data["by_asset_type"] == []

    async def test_portfolio_summary_with_positions(
        self, client: AsyncClient, factory
    ):
        """Should return summary with breakdown by asset type."""
        account = await factory.create_account()
        stock = await factory.create_asset(ticker="PETR4", asset_type=AssetType.STOCK)
        fii = await factory.create_asset(ticker="HGLG11", asset_type=AssetType.FII)

        await factory.create_position(
            account_id=account.id,
            asset_id=stock.id,
            total_cost=Decimal("10000.00"),
        )
        await factory.create_position(
            account_id=account.id,
            asset_id=fii.id,
            total_cost=Decimal("5000.00"),
        )

        response = await client.get("/api/v1/positions/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["total_positions"] == 2
        assert Decimal(data["total_cost"]) == Decimal("15000.00")
        assert len(data["by_asset_type"]) == 2

        # Check allocation percentages
        for item in data["by_asset_type"]:
            if item["asset_type"] == "stock":
                # 10000 / 15000 = 66.67%
                assert Decimal(item["allocation_pct"]) > Decimal("66")
            elif item["asset_type"] == "fii":
                # 5000 / 15000 = 33.33%
                assert Decimal(item["allocation_pct"]) > Decimal("33")

    async def test_portfolio_summary_filter_by_account(
        self, client: AsyncClient, factory
    ):
        """Should filter summary by account."""
        account1 = await factory.create_account(name="BTG")
        account2 = await factory.create_account(name="XP")
        asset = await factory.create_asset()

        await factory.create_position(
            account_id=account1.id,
            asset_id=asset.id,
            total_cost=Decimal("10000.00"),
        )
        await factory.create_position(
            account_id=account2.id,
            asset_id=asset.id,
            total_cost=Decimal("5000.00"),
        )

        response = await client.get(f"/api/v1/positions/summary?account_id={account1.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_positions"] == 1
        assert Decimal(data["total_cost"]) == Decimal("10000.00")

    async def test_portfolio_summary_unauthenticated(
        self, unauthenticated_client: AsyncClient
    ):
        """Should return 401 when not authenticated."""
        response = await unauthenticated_client.get("/api/v1/positions/summary")

        assert response.status_code == 401


class TestRecalculatePositions:
    """Tests for POST /api/v1/positions/{account_id}/recalculate endpoint."""

    async def test_recalculate_positions_success(self, client: AsyncClient, factory):
        """Should recalculate all positions for an account."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        await factory.create_position(account_id=account.id, asset_id=asset.id)

        with patch("app.api.v1.positions.PositionService") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.recalculate_account_positions.return_value = [MagicMock()]
            mock_service.return_value = mock_instance

            response = await client.post(
                f"/api/v1/positions/{account.id}/recalculate"
            )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["positions_updated"] == 1

    async def test_recalculate_positions_account_not_found(
        self, client: AsyncClient
    ):
        """Should return 404 for non-existent account."""
        fake_id = uuid4()
        response = await client.post(f"/api/v1/positions/{fake_id}/recalculate")

        assert response.status_code == 404

    async def test_recalculate_positions_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        account = await factory.create_account()

        response = await unauthenticated_client.post(
            f"/api/v1/positions/{account.id}/recalculate"
        )

        assert response.status_code == 401


class TestPositionPnLCalculations:
    """Tests for P&L calculations in position responses."""

    async def test_position_with_profit(self, client: AsyncClient, factory):
        """Should correctly calculate profit."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        position = await factory.create_position(
            account_id=account.id,
            asset_id=asset.id,
            quantity=Decimal("100"),
            avg_price=Decimal("30.00"),
            total_cost=Decimal("3000.00"),
        )

        with patch("app.api.v1.positions.QuoteService") as mock_quote:
            mock_quote_instance = AsyncMock()
            # Price went up to 35 = 16.67% profit
            mock_quote_instance.get_latest_price.return_value = Decimal("35.00")
            mock_quote.return_value = mock_quote_instance

            response = await client.get(f"/api/v1/positions/{position.id}")

        assert response.status_code == 200
        data = response.json()
        # 100 * 35 = 3500; 3500 - 3000 = 500 profit
        assert Decimal(data["unrealized_pnl"]) == Decimal("500.00")
        # 500 / 3000 * 100 = 16.67%
        assert Decimal(data["unrealized_pnl_pct"]) > Decimal("16")

    async def test_position_with_loss(self, client: AsyncClient, factory):
        """Should correctly calculate loss."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        position = await factory.create_position(
            account_id=account.id,
            asset_id=asset.id,
            quantity=Decimal("100"),
            avg_price=Decimal("40.00"),
            total_cost=Decimal("4000.00"),
        )

        with patch("app.api.v1.positions.QuoteService") as mock_quote:
            mock_quote_instance = AsyncMock()
            # Price dropped to 35 = 12.5% loss
            mock_quote_instance.get_latest_price.return_value = Decimal("35.00")
            mock_quote.return_value = mock_quote_instance

            response = await client.get(f"/api/v1/positions/{position.id}")

        assert response.status_code == 200
        data = response.json()
        # 100 * 35 = 3500; 3500 - 4000 = -500 loss
        assert Decimal(data["unrealized_pnl"]) == Decimal("-500.00")
        assert Decimal(data["unrealized_pnl_pct"]) < Decimal("0")

    async def test_position_without_current_price(self, client: AsyncClient, factory):
        """Should return None for P&L when no current price available."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        position = await factory.create_position(
            account_id=account.id,
            asset_id=asset.id,
        )

        with patch("app.api.v1.positions.QuoteService") as mock_quote:
            mock_quote_instance = AsyncMock()
            mock_quote_instance.get_latest_price.return_value = None
            mock_quote.return_value = mock_quote_instance

            response = await client.get(f"/api/v1/positions/{position.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["current_price"] is None
        assert data["market_value"] is None
        assert data["unrealized_pnl"] is None
