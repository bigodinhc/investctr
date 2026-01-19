"""
Integration tests for Document endpoints.

Tests cover:
- Document upload (with mocked storage)
- Document listing and retrieval
- Document parsing triggers
- Document commit workflow
- Authentication and validation
"""

from io import BytesIO
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.schemas.enums import DocumentType, ParsingStatus
from tests.conftest import TEST_USER_ID


pytestmark = pytest.mark.asyncio


class TestListDocuments:
    """Tests for GET /api/v1/documents endpoint."""

    async def test_list_documents_empty(self, client: AsyncClient):
        """Should return empty list when no documents exist."""
        response = await client.get("/api/v1/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_documents_with_data(self, client: AsyncClient, factory):
        """Should return list of user documents."""
        document = await factory.create_document(
            file_name="extrato_jan_2026.pdf",
            doc_type=DocumentType.STATEMENT,
        )

        response = await client.get("/api/v1/documents")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1

        item = data["items"][0]
        assert item["id"] == str(document.id)
        assert item["file_name"] == "extrato_jan_2026.pdf"
        assert item["doc_type"] == "statement"

    async def test_list_documents_filter_by_status(self, client: AsyncClient, factory):
        """Should filter documents by parsing status."""
        await factory.create_document(parsing_status=ParsingStatus.PENDING)
        await factory.create_document(parsing_status=ParsingStatus.COMPLETED)
        await factory.create_document(parsing_status=ParsingStatus.FAILED)

        response = await client.get("/api/v1/documents?status_filter=completed")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["parsing_status"] == "completed"

    async def test_list_documents_pagination(self, client: AsyncClient, factory):
        """Should support pagination."""
        for i in range(5):
            await factory.create_document(file_name=f"doc_{i}.pdf")

        response = await client.get("/api/v1/documents?skip=2&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_documents_unauthenticated(
        self, unauthenticated_client: AsyncClient
    ):
        """Should return 401 when not authenticated."""
        response = await unauthenticated_client.get("/api/v1/documents")

        assert response.status_code == 401


class TestUploadDocument:
    """Tests for POST /api/v1/documents/upload endpoint."""

    async def test_upload_document_success(self, client: AsyncClient):
        """Should upload a PDF document successfully."""
        pdf_content = b"%PDF-1.4 fake pdf content"

        with patch(
            "app.api.v1.documents.upload_file_to_storage", new_callable=AsyncMock
        ) as mock_upload:
            mock_upload.return_value = f"documents/{TEST_USER_ID}/test.pdf"

            response = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
                data={"doc_type": "statement"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["file_name"] == "test.pdf"
        assert data["doc_type"] == "statement"
        assert data["parsing_status"] == "pending"
        assert "id" in data

        mock_upload.assert_called_once()

    async def test_upload_document_with_account(self, client: AsyncClient, factory):
        """Should associate document with an account."""
        account = await factory.create_account()
        pdf_content = b"%PDF-1.4 fake pdf content"

        with patch(
            "app.api.v1.documents.upload_file_to_storage", new_callable=AsyncMock
        ) as mock_upload:
            mock_upload.return_value = f"documents/{TEST_USER_ID}/test.pdf"

            response = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
                data={
                    "doc_type": "statement",
                    "account_id": str(account.id),
                },
            )

        assert response.status_code == 201
        # Note: account_id association is done but may not be in basic response

    async def test_upload_document_invalid_file_type(self, client: AsyncClient):
        """Should reject non-PDF files."""
        txt_content = b"This is not a PDF"

        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", BytesIO(txt_content), "text/plain")},
            data={"doc_type": "statement"},
        )

        assert response.status_code == 400
        assert "pdf" in response.json()["detail"].lower()

    async def test_upload_document_missing_doc_type(self, client: AsyncClient):
        """Should require doc_type."""
        pdf_content = b"%PDF-1.4 fake pdf content"

        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
        )

        assert response.status_code == 422

    async def test_upload_document_invalid_doc_type(self, client: AsyncClient):
        """Should reject invalid doc_type."""
        pdf_content = b"%PDF-1.4 fake pdf content"

        response = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"doc_type": "invalid_type"},
        )

        assert response.status_code == 422

    async def test_upload_document_storage_error(self, client: AsyncClient):
        """Should handle storage upload errors."""
        pdf_content = b"%PDF-1.4 fake pdf content"

        with patch(
            "app.api.v1.documents.upload_file_to_storage", new_callable=AsyncMock
        ) as mock_upload:
            mock_upload.side_effect = Exception("Storage service unavailable")

            response = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
                data={"doc_type": "statement"},
            )

        assert response.status_code == 500
        assert "storage" in response.json()["detail"].lower()

    async def test_upload_document_unauthenticated(
        self, unauthenticated_client: AsyncClient
    ):
        """Should return 401 when not authenticated."""
        pdf_content = b"%PDF-1.4 fake pdf content"

        response = await unauthenticated_client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")},
            data={"doc_type": "statement"},
        )

        assert response.status_code == 401


class TestGetDocument:
    """Tests for GET /api/v1/documents/{document_id} endpoint."""

    async def test_get_document_success(self, client: AsyncClient, factory):
        """Should return document details including parsed data."""
        document = await factory.create_document(
            file_name="extrato.pdf",
            parsing_status=ParsingStatus.COMPLETED,
            raw_data={"transactions": [{"ticker": "PETR4", "quantity": 100}]},
        )

        response = await client.get(f"/api/v1/documents/{document.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(document.id)
        assert data["file_name"] == "extrato.pdf"
        assert data["parsing_status"] == "completed"
        assert data["raw_extracted_data"] is not None

    async def test_get_document_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent document."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/documents/{fake_id}")

        assert response.status_code == 404

    async def test_get_document_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        document = await factory.create_document()

        response = await unauthenticated_client.get(f"/api/v1/documents/{document.id}")

        assert response.status_code == 401


class TestDeleteDocument:
    """Tests for DELETE /api/v1/documents/{document_id} endpoint."""

    async def test_delete_document_success(self, client: AsyncClient, factory):
        """Should delete document and storage file."""
        document = await factory.create_document()

        with patch(
            "app.api.v1.documents.delete_file_from_storage", new_callable=AsyncMock
        ) as mock_delete:
            response = await client.delete(f"/api/v1/documents/{document.id}")

        assert response.status_code == 204
        mock_delete.assert_called_once()

        # Verify document is deleted
        get_response = await client.get(f"/api/v1/documents/{document.id}")
        assert get_response.status_code == 404

    async def test_delete_document_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent document."""
        fake_id = uuid4()
        response = await client.delete(f"/api/v1/documents/{fake_id}")

        assert response.status_code == 404

    async def test_delete_document_storage_error_continues(
        self, client: AsyncClient, factory
    ):
        """Should continue with DB deletion even if storage delete fails."""
        document = await factory.create_document()

        with patch(
            "app.api.v1.documents.delete_file_from_storage", new_callable=AsyncMock
        ) as mock_delete:
            mock_delete.side_effect = Exception("Storage error")
            response = await client.delete(f"/api/v1/documents/{document.id}")

        # Should still succeed - storage errors are logged but not blocking
        assert response.status_code == 204

    async def test_delete_document_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        document = await factory.create_document()

        response = await unauthenticated_client.delete(
            f"/api/v1/documents/{document.id}"
        )

        assert response.status_code == 401


class TestParseDocument:
    """Tests for POST /api/v1/documents/{document_id}/parse endpoint."""

    async def test_parse_document_async_success(self, client: AsyncClient, factory):
        """Should queue parsing task successfully."""
        document = await factory.create_document(parsing_status=ParsingStatus.PENDING)

        with patch("app.api.v1.documents.parse_document") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "test-task-id"
            mock_task.delay.return_value = mock_result

            response = await client.post(f"/api/v1/documents/{document.id}/parse")

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == str(document.id)
        assert data["task_id"] == "test-task-id"
        assert data["status"] == "pending"

        mock_task.delay.assert_called_once_with(str(document.id), str(TEST_USER_ID))

    async def test_parse_document_already_completed(self, client: AsyncClient, factory):
        """Should reject parsing already completed document."""
        document = await factory.create_document(parsing_status=ParsingStatus.COMPLETED)

        response = await client.post(f"/api/v1/documents/{document.id}/parse")

        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    async def test_parse_document_currently_processing(
        self, client: AsyncClient, factory
    ):
        """Should reject parsing document that is currently processing."""
        document = await factory.create_document(parsing_status=ParsingStatus.PROCESSING)

        response = await client.post(f"/api/v1/documents/{document.id}/parse")

        assert response.status_code == 400
        assert "processing" in response.json()["detail"].lower()

    async def test_parse_document_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent document."""
        fake_id = uuid4()
        response = await client.post(f"/api/v1/documents/{fake_id}/parse")

        assert response.status_code == 404

    async def test_parse_document_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        document = await factory.create_document()

        response = await unauthenticated_client.post(
            f"/api/v1/documents/{document.id}/parse"
        )

        assert response.status_code == 401


class TestReparseDocument:
    """Tests for POST /api/v1/documents/{document_id}/reparse endpoint."""

    async def test_reparse_document_success(self, client: AsyncClient, factory):
        """Should reset and queue reparsing."""
        document = await factory.create_document(
            parsing_status=ParsingStatus.COMPLETED,
            raw_data={"old": "data"},
        )

        with patch("app.api.v1.documents.parse_document") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "new-task-id"
            mock_task.delay.return_value = mock_result

            response = await client.post(f"/api/v1/documents/{document.id}/reparse")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "new-task-id"
        assert data["status"] == "pending"

    async def test_reparse_document_failed(self, client: AsyncClient, factory):
        """Should allow reparsing failed documents."""
        document = await factory.create_document(parsing_status=ParsingStatus.FAILED)

        with patch("app.api.v1.documents.parse_document") as mock_task:
            mock_result = MagicMock()
            mock_result.id = "retry-task-id"
            mock_task.delay.return_value = mock_result

            response = await client.post(f"/api/v1/documents/{document.id}/reparse")

        assert response.status_code == 200

    async def test_reparse_document_currently_processing(
        self, client: AsyncClient, factory
    ):
        """Should reject reparsing document that is currently processing."""
        document = await factory.create_document(parsing_status=ParsingStatus.PROCESSING)

        response = await client.post(f"/api/v1/documents/{document.id}/reparse")

        assert response.status_code == 400

    async def test_reparse_document_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        document = await factory.create_document()

        response = await unauthenticated_client.post(
            f"/api/v1/documents/{document.id}/reparse"
        )

        assert response.status_code == 401


class TestCommitDocument:
    """Tests for POST /api/v1/documents/{document_id}/commit endpoint."""

    async def test_commit_document_success(self, client: AsyncClient, factory):
        """Should commit transactions from parsed document."""
        account = await factory.create_account()
        document = await factory.create_document(
            parsing_status=ParsingStatus.COMPLETED,
            raw_data={"transactions": []},
        )

        payload = {
            "account_id": str(account.id),
            "transactions": [
                {
                    "date": "2026-01-15",
                    "type": "buy",
                    "ticker": "PETR4",
                    "asset_name": "Petrobras PN",
                    "asset_type": "stock",
                    "quantity": "100",
                    "price": "35.50",
                    "total": "3550.00",
                    "fees": "4.90",
                },
                {
                    "date": "2026-01-15",
                    "type": "buy",
                    "ticker": "VALE3",
                    "asset_name": "Vale ON",
                    "quantity": "50",
                    "price": "68.00",
                },
            ],
        }

        with patch("app.api.v1.documents.PositionService") as mock_service:
            mock_instance = AsyncMock()
            mock_instance.calculate_position.return_value = None
            mock_service.return_value = mock_instance

            response = await client.post(
                f"/api/v1/documents/{document.id}/commit",
                json=payload,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == str(document.id)
        assert data["transactions_created"] == 2
        assert data["assets_created"] >= 1  # At least one new asset

    async def test_commit_document_not_parsed(self, client: AsyncClient, factory):
        """Should reject commit for unparsed document."""
        account = await factory.create_account()
        document = await factory.create_document(parsing_status=ParsingStatus.PENDING)

        payload = {
            "account_id": str(account.id),
            "transactions": [
                {
                    "date": "2026-01-15",
                    "type": "buy",
                    "ticker": "PETR4",
                    "quantity": "100",
                    "price": "35.50",
                },
            ],
        }

        response = await client.post(
            f"/api/v1/documents/{document.id}/commit",
            json=payload,
        )

        assert response.status_code == 400
        assert "parsed" in response.json()["detail"].lower()

    async def test_commit_document_invalid_account(self, client: AsyncClient, factory):
        """Should reject commit with invalid account."""
        document = await factory.create_document(parsing_status=ParsingStatus.COMPLETED)
        fake_account_id = uuid4()

        payload = {
            "account_id": str(fake_account_id),
            "transactions": [
                {
                    "date": "2026-01-15",
                    "type": "buy",
                    "ticker": "PETR4",
                    "quantity": "100",
                    "price": "35.50",
                },
            ],
        }

        response = await client.post(
            f"/api/v1/documents/{document.id}/commit",
            json=payload,
        )

        assert response.status_code == 400
        assert "account" in response.json()["detail"].lower()

    async def test_commit_document_empty_transactions(
        self, client: AsyncClient, factory
    ):
        """Should reject commit with empty transactions list."""
        account = await factory.create_account()
        document = await factory.create_document(parsing_status=ParsingStatus.COMPLETED)

        payload = {
            "account_id": str(account.id),
            "transactions": [],
        }

        response = await client.post(
            f"/api/v1/documents/{document.id}/commit",
            json=payload,
        )

        assert response.status_code == 422

    async def test_commit_document_invalid_date(self, client: AsyncClient, factory):
        """Should handle invalid date format gracefully."""
        account = await factory.create_account()
        document = await factory.create_document(parsing_status=ParsingStatus.COMPLETED)

        payload = {
            "account_id": str(account.id),
            "transactions": [
                {
                    "date": "invalid-date",
                    "type": "buy",
                    "ticker": "PETR4",
                    "quantity": "100",
                    "price": "35.50",
                },
            ],
        }

        with patch("app.api.v1.documents.PositionService") as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance

            response = await client.post(
                f"/api/v1/documents/{document.id}/commit",
                json=payload,
            )

        assert response.status_code == 200
        data = response.json()
        # Transaction with invalid date should be in errors
        assert len(data["errors"]) > 0
        assert data["transactions_created"] == 0

    async def test_commit_document_not_found(self, client: AsyncClient, factory):
        """Should return 404 for non-existent document."""
        account = await factory.create_account()
        fake_id = uuid4()

        payload = {
            "account_id": str(account.id),
            "transactions": [
                {
                    "date": "2026-01-15",
                    "type": "buy",
                    "ticker": "PETR4",
                    "quantity": "100",
                    "price": "35.50",
                },
            ],
        }

        response = await client.post(
            f"/api/v1/documents/{fake_id}/commit",
            json=payload,
        )

        assert response.status_code == 404

    async def test_commit_document_unauthenticated(
        self, unauthenticated_client: AsyncClient, factory
    ):
        """Should return 401 when not authenticated."""
        document = await factory.create_document()

        payload = {
            "account_id": str(uuid4()),
            "transactions": [],
        }

        response = await unauthenticated_client.post(
            f"/api/v1/documents/{document.id}/commit",
            json=payload,
        )

        assert response.status_code == 401


class TestDocumentTypes:
    """Tests for different document types."""

    @pytest.mark.parametrize(
        "doc_type",
        ["statement", "trade_note", "income_report", "other"],
    )
    async def test_upload_all_document_types(self, client: AsyncClient, doc_type: str):
        """Should successfully upload documents of all valid types."""
        pdf_content = b"%PDF-1.4 fake pdf content"

        with patch(
            "app.api.v1.documents.upload_file_to_storage", new_callable=AsyncMock
        ) as mock_upload:
            mock_upload.return_value = f"documents/{TEST_USER_ID}/test.pdf"

            response = await client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (f"test_{doc_type}.pdf", BytesIO(pdf_content), "application/pdf")
                },
                data={"doc_type": doc_type},
            )

        assert response.status_code == 201
        assert response.json()["doc_type"] == doc_type
