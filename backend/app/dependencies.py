"""
FastAPI dependency injection functions.
"""

from typing import Annotated

from fastapi import Depends, Header, Request

from app.core.logging import set_request_context
from app.core.security import (
    CurrentUser,
    extract_token_from_header,
    get_user_from_token,
)


async def get_current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        request: FastAPI request object (for setting user context)
        authorization: Authorization header with Bearer token

    Returns:
        CurrentUser with authenticated user information

    Raises:
        HTTPException: If authentication fails
    """
    token = extract_token_from_header(authorization)
    user = get_user_from_token(token)

    # Set user context for logging
    request.state.user_id = str(user.id)
    set_request_context(user_id=str(user.id))

    return user


# Type alias for dependency injection
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
