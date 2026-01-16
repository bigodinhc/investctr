"""
FastAPI dependency injection functions.
"""

from typing import Annotated

from fastapi import Depends, Header

from app.core.security import CurrentUser, extract_token_from_header, get_user_from_token


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        CurrentUser with authenticated user information

    Raises:
        HTTPException: If authentication fails
    """
    token = extract_token_from_header(authorization)
    return get_user_from_token(token)


# Type alias for dependency injection
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
