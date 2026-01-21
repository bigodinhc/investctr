#!/usr/bin/env python3
"""
Batch import statements directly using backend services.

This script processes multiple PDF statements in chronological order,
using the document parsing and commit services directly (bypassing the API).

Usage:
    python -m scripts.batch_import_direct --start-date 2022-11

Or to process specific files:
    python -m scripts.batch_import_direct --files 11-2022.pdf 12-2022.pdf

For other accounts:
    python -m scripts.batch_import_direct --account "Alliance Investments" --start-date 2022-11
    python -m scripts.batch_import_direct --account "BTG Cayman 36595" --parser cayman --base-dir ../Extratos-Cayman
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_maker
from app.models import Account, Document
from app.schemas.enums import DocumentType, ParsingStatus
from app.integrations.claude.parsers import StatementParser, CaymanStatementParser

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent / "Extratos"

# Parser type mapping
PARSER_TYPES = {
    "btg": StatementParser,
    "cayman": CaymanStatementParser,
}


def get_pdf_files(
    start_date: str | None = None,
    end_date: str | None = None,
    specific_files: list[str] | None = None,
) -> list[Path]:
    """Get list of PDF files to process."""
    pdf_files = []

    if specific_files:
        # Process specific files
        for filename in specific_files:
            # Find the file in the directory structure
            for year_dir in BASE_DIR.iterdir():
                if not year_dir.is_dir():
                    continue
                pdf_path = year_dir / filename
                if pdf_path.exists():
                    pdf_files.append(pdf_path)
                    break
        return pdf_files

    # Process by date range
    for year_dir in sorted(BASE_DIR.iterdir()):
        if not year_dir.is_dir():
            continue

        for pdf_file in sorted(year_dir.glob("*.pdf")):
            filename = pdf_file.stem
            parts = filename.split("-")
            if len(parts) != 2:
                continue

            month, file_year = parts
            file_date = f"{file_year}-{month}"

            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue

            pdf_files.append(pdf_file)

    return pdf_files


async def get_account(db: AsyncSession, account_name: str = "BTG Pactual") -> Account:
    """Get an account by name."""
    account_query = select(Account).where(Account.name == account_name)
    result = await db.execute(account_query)
    account = result.scalar_one_or_none()

    if not account:
        raise ValueError(f"Account '{account_name}' not found")

    return account


async def check_if_already_imported(db: AsyncSession, filename: str) -> bool:
    """Check if a file has already been imported."""
    query = select(Document).where(Document.file_name == filename)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    return existing is not None


async def create_document_record(
    db: AsyncSession,
    user_id: UUID,
    account_id: UUID,
    pdf_path: Path,
) -> Document:
    """Create a document record in the database."""
    document = Document(
        user_id=user_id,
        account_id=account_id,
        doc_type=DocumentType.STATEMENT,
        file_name=pdf_path.name,
        file_path=f"local/{pdf_path.name}",  # Mark as local file
        file_size=pdf_path.stat().st_size,
        parsing_status=ParsingStatus.PENDING,
    )
    db.add(document)
    await db.flush()
    return document


async def commit_parsed_data(
    db: AsyncSession,
    document: Document,
    account: Account,
    parsed_data: dict,
) -> dict:
    """Commit parsed data to the database using the documents endpoint logic."""
    from decimal import Decimal
    from app.models import Asset, Transaction, Position, CashFlow, FixedIncomePosition, InvestmentFundPosition
    from app.schemas.enums import TransactionType, CashFlowType, PositionType
    from app.services.position_service import PositionService

    # Use account's currency
    currency = account.currency

    results = {
        "transactions_created": 0,
        "assets_created": 0,
        "positions_updated": 0,
        "fixed_income_created": 0,
        "cash_flows_created": 0,
        "investment_funds_created": 0,
        "equities_processed": 0,
        "derivatives_processed": 0,
        "errors": [],
    }

    # Track new tickers for quote fetching
    new_tickers: set[str] = set()

    # Helper to get or create asset
    async def get_or_create_asset(ticker: str, name: str | None = None, asset_type: str = "stock") -> Asset:
        query = select(Asset).where(Asset.ticker == ticker)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            from app.schemas.enums import AssetType
            # Map asset type string to enum, handling various formats
            asset_type_lower = asset_type.lower() if asset_type else "stock"
            asset_type_enum = AssetType.STOCK
            if asset_type_lower in [e.value for e in AssetType]:
                asset_type_enum = AssetType(asset_type_lower)
            elif asset_type_lower in ("future", "futures"):
                asset_type_enum = AssetType.FUTURE
            elif asset_type_lower in ("option", "options"):
                asset_type_enum = AssetType.OPTION

            asset = Asset(
                ticker=ticker,
                name=name or ticker,
                type=asset_type_enum,
                currency=currency,
            )
            db.add(asset)
            await db.flush()
            results["assets_created"] += 1
            new_tickers.add(ticker)

        return asset

    # 1. Process transactions
    for txn_data in parsed_data.get("transactions", []):
        try:
            ticker = txn_data.get("ticker")
            if not ticker:
                continue

            asset = await get_or_create_asset(
                ticker=ticker,
                name=txn_data.get("asset_name") or txn_data.get("description"),
                asset_type=txn_data.get("asset_type", "stock"),
            )

            # Map transaction type (both PT-BR and English)
            txn_type_str = (txn_data.get("type") or "other").lower()
            type_mapping = {
                # Portuguese
                "buy": TransactionType.BUY,
                "compra": TransactionType.BUY,
                "sell": TransactionType.SELL,
                "venda": TransactionType.SELL,
                "dividend": TransactionType.DIVIDEND,
                "dividendo": TransactionType.DIVIDEND,
                "jcp": TransactionType.JCP,
                "income": TransactionType.INCOME,
                "rendimento": TransactionType.INCOME,
                "split": TransactionType.SPLIT,
                "desdobramento": TransactionType.SPLIT,
                "subscription": TransactionType.SUBSCRIPTION,
                "subscricao": TransactionType.SUBSCRIPTION,
                # English
                "purchase": TransactionType.BUY,
                "sale": TransactionType.SELL,
                "interest": TransactionType.INCOME,
                "fee": TransactionType.FEE,
                "transfer_in": TransactionType.TRANSFER_IN,
                "transfer_out": TransactionType.TRANSFER_OUT,
            }
            txn_type = type_mapping.get(txn_type_str, TransactionType.OTHER)

            # Parse values
            quantity = Decimal(str(txn_data.get("quantity") or 0))
            price = Decimal(str(txn_data.get("price") or 0))
            fees = Decimal(str(txn_data.get("fees") or 0))

            transaction = Transaction(
                account_id=account.id,
                asset_id=asset.id,
                document_id=document.id,
                type=txn_type,
                quantity=quantity,
                price=price,
                fees=fees,
                currency=currency,
                exchange_rate=Decimal("1"),
                executed_at=datetime.strptime(txn_data["date"], "%Y-%m-%d"),
                notes=txn_data.get("notes"),
            )
            db.add(transaction)
            results["transactions_created"] += 1

            # Update position
            position_service = PositionService(db)
            await position_service.update_position_from_transaction(transaction, asset)
            results["positions_updated"] += 1

        except Exception as e:
            results["errors"].append(f"Transaction {txn_data.get('ticker')}: {str(e)}")

    # 2. Process cash movements
    for cm_data in parsed_data.get("cash_movements", {}).get("movements", []):
        try:
            cm_type_str = (cm_data.get("type") or "other").lower()
            type_mapping = {
                # Portuguese
                "deposit": CashFlowType.DEPOSIT,
                "deposito": CashFlowType.DEPOSIT,
                "aporte": CashFlowType.DEPOSIT,
                "withdrawal": CashFlowType.WITHDRAWAL,
                "saque": CashFlowType.WITHDRAWAL,
                "resgate": CashFlowType.WITHDRAWAL,
                "dividend": CashFlowType.DIVIDEND,
                "dividendo": CashFlowType.DIVIDEND,
                "jcp": CashFlowType.JCP,
                "interest": CashFlowType.INTEREST,
                "juros": CashFlowType.INTEREST,
                "rendimento": CashFlowType.INTEREST,
                "fee": CashFlowType.FEE,
                "taxa": CashFlowType.FEE,
                "tarifa": CashFlowType.FEE,
                "tax": CashFlowType.TAX,
                "imposto": CashFlowType.TAX,
                "ir": CashFlowType.TAX,
                "settlement": CashFlowType.SETTLEMENT,
                "liquidacao": CashFlowType.SETTLEMENT,
                # English
                "transfer_in": CashFlowType.DEPOSIT,
                "wire_in": CashFlowType.DEPOSIT,
                "transfer_out": CashFlowType.WITHDRAWAL,
                "wire_out": CashFlowType.WITHDRAWAL,
            }
            cf_type = type_mapping.get(cm_type_str, CashFlowType.OTHER)

            amount = Decimal(str(cm_data.get("value") or cm_data.get("amount") or 0))

            cash_flow = CashFlow(
                account_id=account.id,
                type=cf_type,
                amount=amount,
                currency=currency,
                exchange_rate=Decimal("1"),
                executed_at=datetime.strptime(cm_data["date"], "%Y-%m-%d"),
                notes=cm_data.get("description"),
            )
            db.add(cash_flow)
            results["cash_flows_created"] += 1

        except Exception as e:
            results["errors"].append(f"CashFlow: {str(e)}")

    # 3. Process fixed income positions
    for fi_data in parsed_data.get("fixed_income_positions", []):
        try:
            ref_date = fi_data.get("reference_date")
            if not ref_date:
                # Use period end date or current date
                period = parsed_data.get("period", {})
                ref_date = period.get("end_date") or datetime.now().strftime("%Y-%m-%d")

            # Normalize asset_type to lowercase for enum compatibility
            asset_type_raw = (fi_data.get("asset_type") or "other").lower()
            valid_types = {"cdb", "lca", "lci", "lft", "ntnb", "ntnf", "lf", "debenture", "cri", "cra", "other"}
            asset_type = asset_type_raw if asset_type_raw in valid_types else "other"

            # Normalize indexer to lowercase
            indexer_raw = (fi_data.get("indexer") or "").lower()
            valid_indexers = {"cdi", "selic", "ipca", "igpm", "prefixado", "other"}
            indexer = indexer_raw if indexer_raw in valid_indexers else ("other" if indexer_raw else None)

            fi_position = FixedIncomePosition(
                account_id=account.id,
                document_id=document.id,
                asset_name=fi_data.get("asset_name", "Unknown"),
                asset_type=asset_type,
                issuer=fi_data.get("issuer"),
                quantity=Decimal(str(fi_data.get("quantity") or 1)),
                unit_price=Decimal(str(fi_data.get("unit_price") or 0)) if fi_data.get("unit_price") else None,
                total_value=Decimal(str(fi_data.get("total_value") or 0)),
                indexer=indexer,
                rate_percent=Decimal(str(fi_data.get("rate_percent"))) if fi_data.get("rate_percent") else None,
                acquisition_date=datetime.strptime(fi_data["acquisition_date"], "%Y-%m-%d").date() if fi_data.get("acquisition_date") else None,
                maturity_date=datetime.strptime(fi_data["maturity_date"], "%Y-%m-%d").date() if fi_data.get("maturity_date") else None,
                reference_date=datetime.strptime(ref_date, "%Y-%m-%d").date(),
            )
            db.add(fi_position)
            results["fixed_income_created"] += 1

        except Exception as e:
            results["errors"].append(f"FixedIncome {fi_data.get('asset_name')}: {str(e)}")

    # 4. Process investment funds
    for fund_data in parsed_data.get("investment_funds", []):
        try:
            ref_date = fund_data.get("reference_date")
            if not ref_date:
                period = parsed_data.get("period", {})
                ref_date = period.get("end_date") or datetime.now().strftime("%Y-%m-%d")

            fund_position = InvestmentFundPosition(
                account_id=account.id,
                document_id=document.id,
                fund_name=fund_data.get("fund_name", "Unknown"),
                cnpj=fund_data.get("cnpj"),
                quota_quantity=Decimal(str(fund_data.get("quota_quantity") or 0)),
                quota_price=Decimal(str(fund_data.get("quota_price"))) if fund_data.get("quota_price") else None,
                gross_balance=Decimal(str(fund_data.get("gross_balance") or 0)),
                ir_provision=Decimal(str(fund_data.get("ir_provision"))) if fund_data.get("ir_provision") else None,
                net_balance=Decimal(str(fund_data.get("net_balance"))) if fund_data.get("net_balance") else None,
                reference_date=datetime.strptime(ref_date, "%Y-%m-%d").date(),
            )
            db.add(fund_position)
            results["investment_funds_created"] += 1

        except Exception as e:
            results["errors"].append(f"Fund {fund_data.get('fund_name')}: {str(e)}")

    await db.flush()

    # Trigger quote fetch for new tickers (in background)
    if new_tickers:
        results["new_tickers"] = list(new_tickers)

    return results


async def process_statement(
    db: AsyncSession,
    account: Account,
    pdf_path: Path,
    parser_type: str = "btg",
) -> dict:
    """Process a single statement."""

    print(f"\n{'='*60}")
    print(f"Processing: {pdf_path.name}")
    print(f"Parser: {parser_type}")
    print(f"{'='*60}")

    # Check if already imported
    if await check_if_already_imported(db, pdf_path.name):
        print("  SKIPPED: Already imported")
        return {"file": pdf_path.name, "status": "skipped", "reason": "already imported"}

    # Step 1: Create document record
    print("  [1/3] Creating document record...")
    document = await create_document_record(db, account.user_id, account.id, pdf_path)
    print(f"    Document ID: {document.id}")

    # Step 2: Parse document
    print("  [2/3] Parsing with Claude AI...")
    try:
        # Read PDF content
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()

        # Get the appropriate parser
        parser_class = PARSER_TYPES.get(parser_type, StatementParser)
        parser = parser_class()
        parse_result = await parser.parse(pdf_content)

        if not parse_result.success:
            document.parsing_status = ParsingStatus.FAILED
            document.parsing_error = parse_result.error
            await db.commit()
            raise Exception(f"Parsing failed: {parse_result.error}")

        # Store raw data
        document.raw_extracted_data = parse_result.raw_data
        document.parsing_status = ParsingStatus.COMPLETED
        document.parsed_at = datetime.utcnow()

        parsed_data = parse_result.raw_data

        transactions = parsed_data.get("transactions", [])
        fixed_income = parsed_data.get("fixed_income_positions", [])
        cash_movements = parsed_data.get("cash_movements", {}).get("movements", [])
        investment_funds = parsed_data.get("investment_funds", [])
        equities = parsed_data.get("equities", [])
        derivatives = parsed_data.get("derivatives", [])

        # Show summary based on parser type
        if parser_type == "cayman":
            print(f"    Found: {len(transactions)} transactions, "
                  f"{len(equities)} equities, "
                  f"{len(derivatives)} derivatives, "
                  f"{len(cash_movements)} cash movements")
        else:
            print(f"    Found: {len(transactions)} transactions, "
                  f"{len(fixed_income)} fixed income, "
                  f"{len(cash_movements)} cash movements, "
                  f"{len(investment_funds)} investment funds")

    except Exception as e:
        document.parsing_status = ParsingStatus.FAILED
        document.parsing_error = str(e)
        await db.commit()
        raise Exception(f"Parsing failed: {e}")

    # Step 3: Commit to database
    print("  [3/3] Committing to database...")
    try:
        commit_result = await commit_parsed_data(
            db=db,
            document=document,
            account=account,
            parsed_data=parsed_data,
        )

        await db.commit()

        print(f"    Created: {commit_result.get('transactions_created', 0)} transactions, "
              f"{commit_result.get('assets_created', 0)} assets, "
              f"{commit_result.get('fixed_income_created', 0)} fixed income, "
              f"{commit_result.get('cash_flows_created', 0)} cash flows, "
              f"{commit_result.get('investment_funds_created', 0)} funds")

        if commit_result.get("errors"):
            print(f"    Warnings ({len(commit_result['errors'])}): {commit_result['errors'][:3]}...")

        return {
            "file": pdf_path.name,
            "status": "success",
            "document_id": str(document.id),
            **commit_result,
        }

    except Exception as e:
        await db.rollback()
        raise Exception(f"Commit failed: {e}")


async def main():
    arg_parser = argparse.ArgumentParser(description="Batch import PDF statements directly")
    arg_parser.add_argument(
        "--start-date",
        type=str,
        default="2022-11",
        help="Start month in YYYY-MM format (default: 2022-11)",
    )
    arg_parser.add_argument(
        "--end-date",
        type=str,
        help="End month in YYYY-MM format (inclusive)",
    )
    arg_parser.add_argument(
        "--files",
        nargs="+",
        help="Specific files to process (e.g., 11-2022.pdf 12-2022.pdf)",
    )
    arg_parser.add_argument(
        "--account",
        type=str,
        default="BTG Pactual",
        help="Account name to import to (default: 'BTG Pactual')",
    )
    arg_parser.add_argument(
        "--parser",
        type=str,
        choices=list(PARSER_TYPES.keys()),
        default="btg",
        help="Parser type: 'btg' for BTG Brasil, 'cayman' for BTG Cayman (default: btg)",
    )
    arg_parser.add_argument(
        "--base-dir",
        type=str,
        help="Base directory for PDF files (default: ../Extratos)",
    )
    arg_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files without processing",
    )
    arg_parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing even if a file fails",
    )

    args = arg_parser.parse_args()

    # Set base directory
    base_dir = Path(args.base_dir) if args.base_dir else BASE_DIR

    # Get list of files
    pdf_files = get_pdf_files(
        start_date=args.start_date if not args.files else None,
        end_date=args.end_date if not args.files else None,
        specific_files=args.files,
    )

    # If custom base dir, find files there instead
    if args.base_dir:
        # Simple file finding for custom directory
        pdf_files = sorted(Path(args.base_dir).glob("**/*.pdf"))

    print("=" * 70)
    print("BATCH IMPORT STATEMENTS (Direct)")
    print("=" * 70)
    print(f"Account: {args.account}")
    print(f"Parser: {args.parser}")
    print(f"Source directory: {base_dir}")
    print(f"Files to process: {len(pdf_files)}")
    print()

    if not pdf_files:
        print("No PDF files found matching criteria.")
        return

    print("Files:")
    for pdf_file in pdf_files:
        try:
            print(f"  - {pdf_file.relative_to(base_dir)}")
        except ValueError:
            print(f"  - {pdf_file.name}")

    if args.dry_run:
        print("\n[DRY RUN] No files were processed.")
        return

    print()

    # Initialize database
    session_maker = get_session_maker()

    results = []
    errors = []
    all_new_tickers: set[str] = set()

    async with session_maker() as db:
        # Get account
        account = await get_account(db, args.account)
        print(f"Account: {account.name} ({account.id})")
        print(f"Currency: {account.currency}")
        print(f"User ID: {account.user_id}")
        print()

        for pdf_file in pdf_files:
            try:
                result = await process_statement(
                    db=db,
                    account=account,
                    pdf_path=pdf_file,
                    parser_type=args.parser,
                )
                results.append(result)

                # Collect new tickers
                if result.get("new_tickers"):
                    all_new_tickers.update(result["new_tickers"])

            except Exception as e:
                error_msg = f"{pdf_file.name}: {str(e)}"
                print(f"\n  ERROR: {error_msg}")
                errors.append(error_msg)

                if not args.continue_on_error:
                    print("\nStopping due to error. Use --continue-on-error to continue.")
                    break

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = [r for r in results if r.get("status") == "success"]
    skipped = [r for r in results if r.get("status") == "skipped"]

    print(f"Files processed successfully: {len(successful)}")
    print(f"Files skipped (already imported): {len(skipped)}")
    print(f"Files with errors: {len(errors)}")

    if successful:
        total_transactions = sum(r.get("transactions_created", 0) for r in successful)
        total_assets = sum(r.get("assets_created", 0) for r in successful)
        total_fixed_income = sum(r.get("fixed_income_created", 0) for r in successful)
        total_cash_flows = sum(r.get("cash_flows_created", 0) for r in successful)
        total_funds = sum(r.get("investment_funds_created", 0) for r in successful)

        print(f"\nTotal created:")
        print(f"  - Transactions: {total_transactions}")
        print(f"  - Assets: {total_assets}")
        print(f"  - Fixed Income: {total_fixed_income}")
        print(f"  - Cash Flows: {total_cash_flows}")
        print(f"  - Investment Funds: {total_funds}")

    if all_new_tickers:
        print(f"\nNew tickers created: {len(all_new_tickers)}")
        print(f"  {', '.join(sorted(all_new_tickers)[:20])}{'...' if len(all_new_tickers) > 20 else ''}")

    if errors:
        print("\nErrors:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("1. Run quote backfill: python -m scripts.backfill_quotes")
    print("2. Run NAV backfill: python -m scripts.backfill_nav")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
