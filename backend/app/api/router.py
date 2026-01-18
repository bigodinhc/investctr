"""
Main API router that includes all v1 routes.
"""

from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    assets,
    cash_flows,
    documents,
    fund,
    portfolio,
    positions,
    quotes,
    transactions,
)

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(accounts.router)
api_router.include_router(assets.router)
api_router.include_router(documents.router)
api_router.include_router(transactions.router)
api_router.include_router(positions.router)
api_router.include_router(cash_flows.router)
api_router.include_router(quotes.router)
api_router.include_router(portfolio.router)
api_router.include_router(fund.router)

# Future routers to be added:
# api_router.include_router(risk.router)
