"""
Users API router.

Endpoints for user profile operations. Currently provides the /users/me
endpoint for authenticated users to retrieve their own profile.

WHY A SEPARATE ROUTER FROM AUTH:
Auth endpoints handle identity verification (register, login, tokens).
User endpoints handle user data operations (profile, settings). These
are different concerns that will grow independently as the platform
matures.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    responses={
        401: {"description": "Not authenticated"},
    },
)
def me(current_user: User = Depends(get_current_user)) -> User:
    """
    Return the authenticated user's profile.

    This endpoint requires a valid access token in the Authorization header.
    The user is resolved from the token by the get_current_user dependency.
    """
    return current_user
