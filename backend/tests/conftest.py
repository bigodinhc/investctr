"""
Test configuration and fixtures.

Provides:
- In-memory SQLite database for isolated testing
- Mocked JWT authentication
- Async test client
- Factory fixtures for creating test data
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import CurrentUser
from app.database import Base, get_db
from app.main import app
from app.schemas.enums import (
    AccountType,
    AssetType,
    DocumentType,
    ParsingStatus,
    PositionType,
    TransactionType,
)


# Test database URL - using SQLite for isolation and speed
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Test user UUID
TEST_USER_ID = UUID("12345678-1234-1234-1234-123456789012")
TEST_USER_EMAIL = "test@example.com"


# Pytest configuration
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine with SQLite."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Enable foreign keys for SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Create mock auth.users table for foreign key references
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS "auth.users" (
                    id TEXT PRIMARY KEY
                )
            """)
        )
        # Insert test user
        await conn.execute(
            text('INSERT OR IGNORE INTO "auth.users" (id) VALUES (:user_id)'),
            {"user_id": str(TEST_USER_ID)},
        )

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Alternative name for test_session (for compatibility)."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_current_user() -> CurrentUser:
    """Create a mock authenticated user."""
    return CurrentUser(
        id=TEST_USER_ID,
        email=TEST_USER_EMAIL,
        role="authenticated",
        aal="aal1",
    )


@pytest.fixture
def mock_auth_header() -> dict[str, str]:
    """Create mock authorization header."""
    return {"Authorization": "Bearer test-jwt-token"}


@pytest_asyncio.fixture(scope="function")
async def client(
    test_engine, mock_current_user
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with mocked authentication and database."""

    # Create session maker for this test
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Override database dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session() as session:
            yield session

    # Override authentication dependency
    async def override_get_current_user() -> CurrentUser:
        return mock_current_user

    # Apply overrides
    app.dependency_overrides[get_db] = override_get_db

    # Import the actual dependency to override
    from app.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Create client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def unauthenticated_client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client WITHOUT authentication override.

    This client will return 401 for authenticated endpoints.
    """
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # Note: NOT overriding get_current_user - will use real auth

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# =============================================================================
# Factory Fixtures for Creating Test Data
# =============================================================================


class TestDataFactory:
    """Factory for creating test data objects."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    async def create_account(
        self,
        name: str = "Test Account",
        account_type: AccountType = AccountType.BTG_BR,
        currency: str = "BRL",
        is_active: bool = True,
    ):
        """Create a test account."""
        from app.models import Account

        account = Account(
            id=uuid4(),
            user_id=self.user_id,
            name=name,
            type=account_type,
            currency=currency,
            is_active=is_active,
        )
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def create_asset(
        self,
        ticker: str = "PETR4",
        name: str = "Petrobras PN",
        asset_type: AssetType = AssetType.STOCK,
        currency: str = "BRL",
    ):
        """Create a test asset."""
        from app.models import Asset

        asset = Asset(
            id=uuid4(),
            ticker=ticker,
            name=name,
            asset_type=asset_type,
            currency=currency,
            is_active=True,
        )
        self.session.add(asset)
        await self.session.commit()
        await self.session.refresh(asset)
        return asset

    async def create_transaction(
        self,
        account_id: UUID,
        asset_id: UUID,
        transaction_type: TransactionType = TransactionType.BUY,
        quantity: Decimal = Decimal("100"),
        price: Decimal = Decimal("35.50"),
        fees: Decimal = Decimal("4.90"),
        executed_at: datetime | None = None,
    ):
        """Create a test transaction."""
        from app.models import Transaction

        transaction = Transaction(
            id=uuid4(),
            account_id=account_id,
            asset_id=asset_id,
            type=transaction_type,
            quantity=quantity,
            price=price,
            fees=fees,
            currency="BRL",
            exchange_rate=Decimal("1"),
            executed_at=executed_at or datetime.utcnow(),
        )
        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)
        return transaction

    async def create_position(
        self,
        account_id: UUID,
        asset_id: UUID,
        quantity: Decimal = Decimal("100"),
        avg_price: Decimal = Decimal("35.50"),
        total_cost: Decimal = Decimal("3550.00"),
        position_type: PositionType = PositionType.LONG,
    ):
        """Create a test position."""
        from app.models import Position

        position = Position(
            id=uuid4(),
            account_id=account_id,
            asset_id=asset_id,
            quantity=quantity,
            avg_price=avg_price,
            total_cost=total_cost,
            position_type=position_type,
            opened_at=datetime.utcnow(),
        )
        self.session.add(position)
        await self.session.commit()
        await self.session.refresh(position)
        return position

    async def create_document(
        self,
        file_name: str = "test_statement.pdf",
        doc_type: DocumentType = DocumentType.STATEMENT,
        account_id: UUID | None = None,
        parsing_status: ParsingStatus = ParsingStatus.PENDING,
        raw_data: dict | None = None,
    ):
        """Create a test document."""
        from app.models import Document

        document = Document(
            id=uuid4(),
            user_id=self.user_id,
            account_id=account_id,
            doc_type=doc_type,
            file_name=file_name,
            file_path=f"documents/{self.user_id}/{file_name}",
            file_size=1024,
            parsing_status=parsing_status,
            raw_extracted_data=raw_data,
        )
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)
        return document


@pytest_asyncio.fixture
async def factory(test_session) -> TestDataFactory:
    """Create a test data factory."""
    return TestDataFactory(test_session, TEST_USER_ID)


@pytest_asyncio.fixture
async def test_account(factory: TestDataFactory):
    """Create a default test account."""
    return await factory.create_account()


@pytest_asyncio.fixture
async def test_asset(factory: TestDataFactory):
    """Create a default test asset."""
    return await factory.create_asset()


# =============================================================================
# Mock Fixtures for External Services
# =============================================================================


@pytest.fixture
def mock_supabase_storage():
    """Mock Supabase storage operations."""
    with patch("app.integrations.supabase.upload_file_to_storage") as mock_upload, \
         patch("app.integrations.supabase.delete_file_from_storage") as mock_delete:

        async def fake_upload(bucket: str, path: str, content: bytes, content_type: str):
            return path

        async def fake_delete(bucket: str, path: str):
            pass

        mock_upload.side_effect = fake_upload
        mock_delete.side_effect = fake_delete

        yield {
            "upload": mock_upload,
            "delete": mock_delete,
        }


@pytest.fixture
def mock_celery_task():
    """Mock Celery task execution."""
    mock_task = MagicMock()
    mock_task.delay.return_value = MagicMock(id="test-task-id")

    with patch("app.workers.tasks.parse_document", mock_task):
        yield mock_task


@pytest.fixture
def mock_quote_service():
    """Mock quote service for price lookups."""
    with patch("app.services.quote_service.QuoteService") as mock_class:
        mock_instance = AsyncMock()
        mock_instance.get_latest_price.return_value = Decimal("40.00")
        mock_instance.get_latest_prices.return_value = {}
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_pnl_service():
    """Mock P&L service calculations."""
    with patch("app.services.pnl_service.PnLService") as mock_class:
        mock_instance = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance
