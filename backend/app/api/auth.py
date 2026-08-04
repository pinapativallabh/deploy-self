"""
Authentication API router.

WHY THIS IS THIN:
Every endpoint here follows the same pattern:
  1. Parse and validate the request (FastAPI + Pydantic do this automatically)
  2. Call the auth service with the validated data
  3. Convert the service response to an HTTP response

Business logic lives in auth_service.py. This router only handles HTTP
concerns: status codes, response models, and dependency injection.

WHY AuthError IS CAUGHT AT THE ROUTER LEVEL:
The auth service raises AuthError with a status_code and detail message.
The router catches these and converts them to HTTPException. This keeps
the service free of HTTP imports while giving the router full control
over response formatting.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_raw_token, get_redis, RateLimiter
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    AuthError,
    authenticate_user,
    create_login_tokens,
    logout_user,
    refresh_tokens,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("app.api.auth")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new user",
    responses={
        409: {"description": "Email or username already taken"},
        422: {"description": "Validation error"},
    },
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(max_requests=settings.RATE_LIMIT_REGISTER_MAX, window_seconds=settings.RATE_LIMIT_REGISTER_WINDOW)),
) -> User:
    """
    Create a new user account.

    Validates that email and username are unique, hashes the password,
    and returns the created user profile.
    """
    try:
        return register_user(db, data)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive tokens",
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _rate_limit: None = Depends(RateLimiter(max_requests=settings.RATE_LIMIT_LOGIN_MAX, window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW)),
) -> TokenResponse:
    """
    Authenticate with email/username and password.

    Returns an access token (short-lived) and refresh token (long-lived).
    """
    try:
        user = authenticate_user(db, data)
        return await create_login_tokens(redis, user)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh tokens",
    responses={
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh(
    data: RefreshRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new token pair.

    The old refresh token is revoked (token rotation). If the old token
    has already been used, the request is rejected.
    """
    try:
        return await refresh_tokens(db, redis, data.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout and revoke current token",
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def logout(
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    token: str = Depends(get_raw_token),
) -> MessageResponse:
    """
    Revoke the current access token.

    The token is added to a Redis blocklist for its remaining lifetime.
    Subsequent requests with the same token will be rejected.
    """
    await logout_user(redis, token)
    return MessageResponse(message="Successfully logged out.")
