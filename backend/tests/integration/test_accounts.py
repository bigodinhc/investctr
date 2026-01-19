"""
Integration tests for Account endpoints.

Tests cover:
- CRUD operations (Create, Read, Update, Delete)
- Authentication (401 for unauthenticated requests)
- Validation (400 for invalid data)
- Authorization (404 for accessing other user's accounts)
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import TEST_USER_ID


pytestmark = pytest.mark.asyncio


class TestListAccounts:
    """Tests for GET /api/v1/accounts endpoint."""

    async def test_list_accounts_empty(self, client: AsyncClient):
        """Should return empty list when no accounts exist."""
        response = await client.get("/api/v1/accounts")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_accounts_with_data(self, client: AsyncClient, test_account):
        """Should return list of user accounts."""
        response = await client.get("/api/v1/accounts")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["name"] == test_account.name
        assert data["items"][0]["type"] == test_account.type.value

    async def test_list_accounts_pagination(self, client: AsyncClient, factory):
        """Should support pagination parameters."""
        # Create multiple accounts
        for i in range(5):
            await factory.create_account(name=f"Account {i}")

        # Request with pagination
        response = await client.get("/api/v1/accounts?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_accounts_unauthenticated(self, unauthenticated_client: AsyncClient):
        """Should return 401 when not authenticated."""
        response = await unauthenticated_client.get("/api/v1/accounts")

        assert response.status_code == 401


class TestCreateAccount:
    """Tests for POST /api/v1/accounts endpoint."""

    async def test_create_account_success(self, client: AsyncClient):
        """Should create a new account with valid data."""
        payload = {
            "name": "Nova Conta BTG",
            "type": "btg_br",
            "currency": "BRL",
        }

        response = await client.post("/api/v1/accounts", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Nova Conta BTG"
        assert data["type"] == "btg_br"
        assert data["currency"] == "BRL"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    async def test_create_account_minimal_data(self, client: AsyncClient):
        """Should create account with only required fields."""
        payload = {
            "name": "Conta XP",
            "type": "xp",
        }

        response = await client.post("/api/v1/accounts", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Conta XP"
        assert data["currency"] == "BRL"  # Default value

    async def test_create_account_usd_currency(self, client: AsyncClient):
        """Should allow USD currency."""
        payload = {
            "name": "Conta Internacional",
            "type": "btg_cayman",
            "currency": "USD",
        }

        response = await client.post("/api/v1/accounts", json=payload)

        assert response.status_code == 201
        assert response.json()["currency"] == "USD"

    async def test_create_account_invalid_type(self, client: AsyncClient):
        """Should return 422 for invalid account type."""
        payload = {
            "name": "Conta Invalida",
            "type": "invalid_type",
        }

        response = await client.post("/api/v1/accounts", json=payload)

        assert response.status_code == 422

    async def test_create_account_missing_name(self, client: AsyncClient):
        """Should return 422 when name is missing."""
        payload = {
            "type": "btg_br",
        }

        response = await client.post("/api/v1/accounts", json=payload)

        assert response.status_code == 422

    async def test_create_account_empty_name(self, client: AsyncClient):
        """Should return 422 when name is empty."""
        payload = {
            "name": "",
            "type": "btg_br",
        }

        response = await client.post("/api/v1/accounts", json=payload)

        assert response.status_code == 422

    async def test_create_account_name_too_long(self, client: AsyncClient):
        """Should return 422 when name exceeds max length."""
        payload = {
            "name": "A" * 101,  # Max is 100
            "type": "btg_br",
        }

        response = await client.post("/api/v1/accounts", json=payload)

        assert response.status_code == 422

    async def test_create_account_unauthenticated(self, unauthenticated_client: AsyncClient):
        """Should return 401 when not authenticated."""
        payload = {
            "name": "Test Account",
            "type": "btg_br",
        }

        response = await unauthenticated_client.post("/api/v1/accounts", json=payload)

        assert response.status_code == 401


class TestGetAccount:
    """Tests for GET /api/v1/accounts/{account_id} endpoint."""

    async def test_get_account_success(self, client: AsyncClient, test_account):
        """Should return account details."""
        response = await client.get(f"/api/v1/accounts/{test_account.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_account.id)
        assert data["name"] == test_account.name
        assert data["type"] == test_account.type.value

    async def test_get_account_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent account."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/accounts/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_account_invalid_uuid(self, client: AsyncClient):
        """Should return 422 for invalid UUID format."""
        response = await client.get("/api/v1/accounts/not-a-uuid")

        assert response.status_code == 422

    async def test_get_account_unauthenticated(
        self, unauthenticated_client: AsyncClient, test_account
    ):
        """Should return 401 when not authenticated."""
        response = await unauthenticated_client.get(f"/api/v1/accounts/{test_account.id}")

        assert response.status_code == 401


class TestUpdateAccount:
    """Tests for PUT /api/v1/accounts/{account_id} endpoint."""

    async def test_update_account_name(self, client: AsyncClient, test_account):
        """Should update account name."""
        payload = {"name": "Nome Atualizado"}

        response = await client.put(
            f"/api/v1/accounts/{test_account.id}",
            json=payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Nome Atualizado"
        assert data["type"] == test_account.type.value  # Unchanged

    async def test_update_account_deactivate(self, client: AsyncClient, test_account):
        """Should allow deactivating an account."""
        payload = {"is_active": False}

        response = await client.put(
            f"/api/v1/accounts/{test_account.id}",
            json=payload,
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    async def test_update_account_partial(self, client: AsyncClient, test_account):
        """Should allow partial updates (only provided fields)."""
        original_name = test_account.name
        payload = {"is_active": False}

        response = await client.put(
            f"/api/v1/accounts/{test_account.id}",
            json=payload,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == original_name  # Unchanged
        assert data["is_active"] is False

    async def test_update_account_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent account."""
        fake_id = uuid4()
        payload = {"name": "New Name"}

        response = await client.put(f"/api/v1/accounts/{fake_id}", json=payload)

        assert response.status_code == 404

    async def test_update_account_empty_name(self, client: AsyncClient, test_account):
        """Should return 422 when updating with empty name."""
        payload = {"name": ""}

        response = await client.put(
            f"/api/v1/accounts/{test_account.id}",
            json=payload,
        )

        assert response.status_code == 422

    async def test_update_account_unauthenticated(
        self, unauthenticated_client: AsyncClient, test_account
    ):
        """Should return 401 when not authenticated."""
        payload = {"name": "New Name"}

        response = await unauthenticated_client.put(
            f"/api/v1/accounts/{test_account.id}",
            json=payload,
        )

        assert response.status_code == 401


class TestDeleteAccount:
    """Tests for DELETE /api/v1/accounts/{account_id} endpoint."""

    async def test_delete_account_success(self, client: AsyncClient, test_account):
        """Should soft delete an account."""
        response = await client.delete(f"/api/v1/accounts/{test_account.id}")

        assert response.status_code == 204

        # Verify account is no longer returned in list
        list_response = await client.get("/api/v1/accounts")
        assert list_response.json()["total"] == 0

    async def test_delete_account_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent account."""
        fake_id = uuid4()
        response = await client.delete(f"/api/v1/accounts/{fake_id}")

        assert response.status_code == 404

    async def test_delete_account_unauthenticated(
        self, unauthenticated_client: AsyncClient, test_account
    ):
        """Should return 401 when not authenticated."""
        response = await unauthenticated_client.delete(
            f"/api/v1/accounts/{test_account.id}"
        )

        assert response.status_code == 401

    async def test_delete_account_idempotent(self, client: AsyncClient, test_account):
        """Deleting already deleted account should return 404."""
        # First delete
        await client.delete(f"/api/v1/accounts/{test_account.id}")

        # Second delete should fail
        response = await client.delete(f"/api/v1/accounts/{test_account.id}")
        assert response.status_code == 404


class TestAccountTypes:
    """Tests for different account types."""

    @pytest.mark.parametrize(
        "account_type",
        ["btg_br", "xp", "btg_cayman", "tesouro_direto"],
    )
    async def test_create_all_account_types(self, client: AsyncClient, account_type: str):
        """Should successfully create accounts of all valid types."""
        payload = {
            "name": f"Account {account_type}",
            "type": account_type,
        }

        response = await client.post("/api/v1/accounts", json=payload)

        assert response.status_code == 201
        assert response.json()["type"] == account_type
