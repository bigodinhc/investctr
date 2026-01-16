"""
API-specific dependencies.
"""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AuthenticatedUser, get_current_user


# Re-export for convenience
__all__ = ["AuthenticatedUser", "get_current_user", "PaginationParams", "DBSession"]

# Database session dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]


class PaginationParams:
    """Common pagination parameters."""

    def __init__(
        self,
        skip: Annotated[int, Query(ge=0, description="Number of records to skip")] = 0,
        limit: Annotated[
            int, Query(ge=1, le=100, description="Maximum number of records to return")
        ] = 50,
    ):
        self.skip = skip
        self.limit = limit


Pagination = Annotated[PaginationParams, Depends()]
