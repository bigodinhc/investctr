"""
Integration tests for Transaction endpoints.

Tests cover:
- CRUD operations for transactions
- Position recalculation after transaction changes
- Filtering by account, asset, type, and date range
- Authentication and validation
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.schemas.enums import TransactionType


pytestmark = pytest.mark.asyncio


class TestListTransactions:
    """Tests for GET /api/v1/transactions endpoint."""

    async def test_list_transactions_empty(self, client: AsyncClient):
        """Should return empty list when no transactions exist."""
        response = await client.get("/api/v1/transactions")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_transactions_with_data(
        self, client: AsyncClient, factory
    ):
        """Should return list of user transactions with asset info."""
        # Setup: Create account, asset, and transaction
        account = await factory.create_account()
        asset = await factory.create_asset(ticker="VALE3", name="Vale ON")
        transaction = await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            quantity=Decimal("100"),
            price=Decimal("68.50"),
        )

        response = await client.get("/api/v1/transactions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1

        item = data["items"][0]
        assert item["id"] == str(transaction.id)
        assert item["ticker"] == "VALE3"
        assert item["asset_name"] == "Vale ON"
        assert item["quantity"] == "100.00000000"
        assert item["type"] == "buy"

    async def test_list_transactions_filter_by_account(
        self, client: AsyncClient, factory
    ):
        """Should filter transactions by account_id."""
        account1 = await factory.create_account(name="Account 1")
        account2 = await factory.create_account(name="Account 2")
        asset = await factory.create_asset()

        await factory.create_transaction(account_id=account1.id, asset_id=asset.id)
        await factory.create_transaction(account_id=account2.id, asset_id=asset.id)

        response = await client.get(f"/api/v1/transactions?account_id={account1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["account_id"] == str(account1.id)

    async def test_list_transactions_filter_by_asset(
        self, client: AsyncClient, factory
    ):
        """Should filter transactions by asset_id."""
        account = await factory.create_account()
        asset1 = await factory.create_asset(ticker="PETR4")
        asset2 = await factory.create_asset(ticker="VALE3")

        await factory.create_transaction(account_id=account.id, asset_id=asset1.id)
        await factory.create_transaction(account_id=account.id, asset_id=asset2.id)

        response = await client.get(f"/api/v1/transactions?asset_id={asset1.id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["asset_id"] == str(asset1.id)

    async def test_list_transactions_filter_by_type(
        self, client: AsyncClient, factory
    ):
        """Should filter transactions by type."""
        account = await factory.create_account()
        asset = await factory.create_asset()

        await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
        )
        await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
            transaction_type=TransactionType.SELL,
        )

        response = await client.get("/api/v1/transactions?type_filter=buy")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["type"] == "buy"

    async def test_list_transactions_filter_by_date_range(
        self, client: AsyncClient, factory
    ):
        """Should filter transactions by date range."""
        account = await factory.create_account()
        asset = await factory.create_asset()

        today = datetime.utcnow()
        last_week = today - timedelta(days=7)

        await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
            executed_at=today,
        )
        await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
            executed_at=last_week,
        )

        # Filter for last 3 days
        start = (today - timedelta(days=3)).isoformat()
        end = today.isoformat()

        response = await client.get(
            f"/api/v1/transactions?start_date={start}&end_date={end}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

    async def test_list_transactions_pagination(self, client: AsyncClient, factory):
        """Should support pagination."""
        account = await factory.create_account()
        asset = await factory.create_asset()

        for _ in range(5):
            await factory.create_transaction(account_id=account.id, asset_id=asset.id)

        response = await client.get("/api/v1/transactions?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_transactions_unauthenticated(
        self, unauthenticated_client: AsyncClient
    ):
        """Should return 401 when not authenticated."""
        response = await unauthenticated_client.get("/api/v1/transactions")

        assert response.status_code == 401


class TestCreateTransaction:
    """Tests for POST /api/v1/transactions endpoint."""

    async def test_create_transaction_success(self, client: AsyncClient, factory):
        """Should create a new transaction with valid data."""
        account = await factory.create_account()
        asset = await factory.create_asset()

        payload = {
            "account_id": str(account.id),
            "asset_id": str(asset.id),
            "type": "buy",
            "quantity": "100",
            "price": "35.50",
            "fees": "4.90",
            "currency": "BRL",
            "executed_at": datetime.utcnow().isoformat(),
        }

        # Mock position recalculation
        with patch(
            "app.api.v1.transactions.recalculate_positions_after_transaction",
            new_callable=AsyncMock,
        ):
            response = await client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "buy"
        assert data["quantity"] == "100.00000000"
        assert data["price"] == "35.500000"
        assert "id" in data

    async def test_create_transaction_sell(self, client: AsyncClient, factory):
        """Should create a sell transaction."""
        account = await factory.create_account()
        asset = await factory.create_asset()

        payload = {
            "account_id": str(account.id),
            "asset_id": str(asset.id),
            "type": "sell",
            "quantity": "50",
            "price": "40.00",
            "executed_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "app.api.v1.transactions.recalculate_positions_after_transaction",
            new_callable=AsyncMock,
        ):
            response = await client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 201
        assert response.json()["type"] == "sell"

    async def test_create_transaction_dividend(self, client: AsyncClient, factory):
        """Should create a dividend transaction."""
        account = await factory.create_account()
        asset = await factory.create_asset()

        payload = {
            "account_id": str(account.id),
            "asset_id": str(asset.id),
            "type": "dividend",
            "quantity": "100",
            "price": "0.50",  # Dividend per share
            "executed_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "app.api.v1.transactions.recalculate_positions_after_transaction",
            new_callable=AsyncMock,
        ):
            response = await client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 201
        assert response.json()["type"] == "dividend"

    async def test_create_transaction_invalid_account(self, client: AsyncClient, factory):
        """Should return 400 when account doesn't exist or belong to user."""
        asset = await factory.create_asset()
        fake_account_id = uuid4()

        payload = {
            "account_id": str(fake_account_id),
            "asset_id": str(asset.id),
            "type": "buy",
            "quantity": "100",
            "price": "35.50",
            "executed_at": datetime.utcnow().isoformat(),
        }

        response = await client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 400
        assert "account" in response.json()["detail"].lower()

    async def test_create_transaction_invalid_asset(self, client: AsyncClient, factory):
        """Should return 400 when asset doesn't exist."""
        account = await factory.create_account()
        fake_asset_id = uuid4()

        payload = {
            "account_id": str(account.id),
            "asset_id": str(fake_asset_id),
            "type": "buy",
            "quantity": "100",
            "price": "35.50",
            "executed_at": datetime.utcnow().isoformat(),
        }

        response = await client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 400
        assert "asset" in response.json()["detail"].lower()

    async def test_create_transaction_invalid_type(self, client: AsyncClient, factory):
        """Should return 422 for invalid transaction type."""
        account = await factory.create_account()
        asset = await factory.create_asset()

        payload = {
            "account_id": str(account.id),
            "asset_id": str(asset.id),
            "type": "invalid_type",
            "quantity": "100",
            "price": "35.50",
            "executed_at": datetime.utcnow().isoformat(),
        }

        response = await client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 422

    async def test_create_transaction_negative_price(self, client: AsyncClient, factory):
        """Should return 422 for negative price."""
        account = await factory.create_account()
        asset = await factory.create_asset()

        payload = {
            "account_id": str(account.id),
            "asset_id": str(asset.id),
            "type": "buy",
            "quantity": "100",
            "price": "-35.50",
            "executed_at": datetime.utcnow().isoformat(),
        }

        response = await client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 422

    async def test_create_transaction_missing_required_fields(
        self, client: AsyncClient
    ):
        """Should return 422 when required fields are missing."""
        payload = {
            "type": "buy",
        }

        response = await client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 422

    async def test_create_transaction_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        payload = {
            "account_id": str(uuid4()),
            "asset_id": str(uuid4()),
            "type": "buy",
            "quantity": "100",
            "price": "35.50",
            "executed_at": datetime.utcnow().isoformat(),
        }

        response = await unauthenticated_client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 401


class TestGetTransaction:
    """Tests for GET /api/v1/transactions/{transaction_id} endpoint."""

    async def test_get_transaction_success(self, client: AsyncClient, factory):
        """Should return transaction details with asset info."""
        account = await factory.create_account()
        asset = await factory.create_asset(ticker="ITUB4", name="Itau Unibanco PN")
        transaction = await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
        )

        response = await client.get(f"/api/v1/transactions/{transaction.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(transaction.id)
        assert data["ticker"] == "ITUB4"
        assert data["asset_name"] == "Itau Unibanco PN"

    async def test_get_transaction_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent transaction."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/transactions/{fake_id}")

        assert response.status_code == 404

    async def test_get_transaction_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        transaction = await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
        )

        response = await unauthenticated_client.get(
            f"/api/v1/transactions/{transaction.id}"
        )

        assert response.status_code == 401


class TestUpdateTransaction:
    """Tests for PUT /api/v1/transactions/{transaction_id} endpoint."""

    async def test_update_transaction_quantity(self, client: AsyncClient, factory):
        """Should update transaction quantity."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        transaction = await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
            quantity=Decimal("100"),
        )

        payload = {"quantity": "200"}

        with patch(
            "app.api.v1.transactions.recalculate_positions_after_transaction",
            new_callable=AsyncMock,
        ):
            response = await client.put(
                f"/api/v1/transactions/{transaction.id}",
                json=payload,
            )

        assert response.status_code == 200
        assert response.json()["quantity"] == "200.00000000"

    async def test_update_transaction_price(self, client: AsyncClient, factory):
        """Should update transaction price."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        transaction = await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
            price=Decimal("35.50"),
        )

        payload = {"price": "40.00"}

        with patch(
            "app.api.v1.transactions.recalculate_positions_after_transaction",
            new_callable=AsyncMock,
        ):
            response = await client.put(
                f"/api/v1/transactions/{transaction.id}",
                json=payload,
            )

        assert response.status_code == 200
        assert response.json()["price"] == "40.000000"

    async def test_update_transaction_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent transaction."""
        fake_id = uuid4()
        payload = {"quantity": "200"}

        response = await client.put(f"/api/v1/transactions/{fake_id}", json=payload)

        assert response.status_code == 404

    async def test_update_transaction_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        transaction = await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
        )

        payload = {"quantity": "200"}

        response = await unauthenticated_client.put(
            f"/api/v1/transactions/{transaction.id}",
            json=payload,
        )

        assert response.status_code == 401


class TestDeleteTransaction:
    """Tests for DELETE /api/v1/transactions/{transaction_id} endpoint."""

    async def test_delete_transaction_success(self, client: AsyncClient, factory):
        """Should delete a transaction."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        transaction = await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
        )

        with patch(
            "app.api.v1.transactions.recalculate_positions_after_transaction",
            new_callable=AsyncMock,
        ):
            response = await client.delete(f"/api/v1/transactions/{transaction.id}")

        assert response.status_code == 204

        # Verify transaction is deleted
        get_response = await client.get(f"/api/v1/transactions/{transaction.id}")
        assert get_response.status_code == 404

    async def test_delete_transaction_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent transaction."""
        fake_id = uuid4()
        response = await client.delete(f"/api/v1/transactions/{fake_id}")

        assert response.status_code == 404

    async def test_delete_transaction_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        account = await factory.create_account()
        asset = await factory.create_asset()
        transaction = await factory.create_transaction(
            account_id=account.id,
            asset_id=asset.id,
        )

        response = await unauthenticated_client.delete(
            f"/api/v1/transactions/{transaction.id}"
        )

        assert response.status_code == 401


class TestTransactionTypes:
    """Tests for different transaction types."""

    @pytest.mark.parametrize(
        "tx_type",
        [
            "buy",
            "sell",
            "dividend",
            "jcp",
            "income",
            "amortization",
            "split",
            "subscription",
            "transfer_in",
            "transfer_out",
            "rental",
            "other",
        ],
    )
    async def test_create_all_transaction_types(
        self, client: AsyncClient, factory, tx_type: str
    ):
        """Should successfully create transactions of all valid types."""
        account = await factory.create_account()
        asset = await factory.create_asset()

        payload = {
            "account_id": str(account.id),
            "asset_id": str(asset.id),
            "type": tx_type,
            "quantity": "100",
            "price": "10.00",
            "executed_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "app.api.v1.transactions.recalculate_positions_after_transaction",
            new_callable=AsyncMock,
        ):
            response = await client.post("/api/v1/transactions", json=payload)

        assert response.status_code == 201
        assert response.json()["type"] == tx_type
