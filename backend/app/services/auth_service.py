"""
Authentication service.

WHY THIS EXISTS:
Business logic for registration, login, token refresh, and logout lives here
— NOT in the router. Routers handle HTTP concerns (request parsing, status
codes, response serialization). Services handle domain logic (does this user
exist? is the password correct? should this token be rotated?).

This separation means:
  - Routers stay thin and readable
  - Business logic can be tested without HTTP
  - Multiple routers or CLI tools can reuse the same service

WHY REDIS FOR TOKEN REVOCATION:
JWTs are stateless — once issued, they're valid until expiry. To support
logout and token rotation, we need a revocation mechanism. Options:
  1. Database blocklist — works but adds a DB query to every authenticated request
  2. Redis blocklist — sub-millisecond lookups, automatic TTL expiry
  3. Short-lived tokens only — poor UX (frequent re-login)

Redis is the right choice: it's already in our stack, lookups are O(1), and
the TTL feature automatically cleans up expired entries.

WHY TOKEN ROTATION ON REFRESH:
When a refresh token is used, we revoke it and issue a new pair. This limits
the window of compromise: if an attacker steals a refresh token, either the
attacker or the legitimate user will use it first. The second use attempt
will fail because the token was already rotated. Without rotation, a stolen
refresh token grants access for its entire lifetime.
"""

import logging

import jwt
from redis.asyncio import Redis
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)

logger = logging.getLogger("app.auth")


class AuthError(Exception):
    """
    Authentication/authorization error with an HTTP status code.

    Raised by the auth service when an operation fails for a known reason.
    The router catches these and converts them to HTTP responses.
    """

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


# --- Redis Key Helpers ---

def _revoked_token_key(jti: str) -> str:
    """Redis key for a revoked token. Prefixed for namespace isolation."""
    return f"revoked_token:{jti}"


def _active_refresh_key(user_id: str, jti: str) -> str:
    """Redis key for an active refresh token. Links user to their refresh token."""
    return f"active_refresh:{user_id}:{jti}"


# --- Registration ---

def register_user(db: Session, data: RegisterRequest) -> User:
    """
    Create a new user account.

    Validates uniqueness of email and username, hashes the password, and
    persists the user. Returns the created User ORM instance.

    Raises:
        AuthError: If email or username is already taken.
    """
    # Check for existing email
    existing_email = db.query(User).filter(User.email == data.email).first()
    if existing_email:
        raise AuthError("A user with this email already exists.", status_code=409)

    # Check for existing username
    existing_username = db.query(User).filter(User.username == data.username).first()
    if existing_username:
        raise AuthError("A user with this username already exists.", status_code=409)

    user = User(
        email=data.email,
        username=data.username,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("User registered: %s (%s)", user.username, user.id)
    return user


# --- Login ---

def authenticate_user(db: Session, data: LoginRequest) -> User:
    """
    Authenticate a user by email/username and password.

    The login field can be either an email or a username. We check both
    columns in a single query to avoid revealing which identifier type
    the system accepts (defense against enumeration).

    Raises:
        AuthError: If credentials are invalid. Uses a generic message to
                   prevent user enumeration.
    """
    user = (
        db.query(User)
        .filter(or_(User.email == data.login, User.username == data.login))
        .first()
    )

    if not user or not verify_password(data.password, user.password_hash):
        raise AuthError("Invalid credentials.", status_code=401)

    return user


async def create_login_tokens(redis: Redis, user: User) -> TokenResponse:
    """
    Generate a token pair and register the refresh token in Redis.

    The refresh token's jti is stored in Redis with a TTL matching the
    token's expiry. This serves two purposes:
      1. We can verify the refresh token is still active (not revoked)
      2. Redis automatically cleans up expired entries
    """
    access_token, refresh_token, access_jti, refresh_jti = create_token_pair(
        str(user.id)
    )

    # Store refresh token jti in Redis so we can validate it on refresh
    refresh_ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400  # days -> seconds
    await redis.set(
        _active_refresh_key(str(user.id), refresh_jti),
        "1",
        ex=refresh_ttl,
    )

    logger.info("Login successful: %s (%s)", user.username, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# --- Token Refresh ---

async def refresh_tokens(db: Session, redis: Redis, refresh_token_str: str) -> TokenResponse:
    """
    Rotate tokens: validate the refresh token, revoke it, issue a new pair.

    Token rotation flow:
      1. Decode the refresh token
      2. Verify it's a refresh token (not an access token)
      3. Verify it hasn't been revoked (exists in Redis active set)
      4. Verify the user still exists in the database
      5. Revoke the old refresh token
      6. Issue a new token pair

    Raises:
        AuthError: If the token is invalid, expired, revoked, or the user
                   no longer exists.
    """
    try:
        payload = decode_token(refresh_token_str)
    except jwt.ExpiredSignatureError:
        raise AuthError("Refresh token has expired.", status_code=401)
    except jwt.InvalidTokenError:
        raise AuthError("Invalid refresh token.", status_code=401)

    if payload.get("type") != "refresh":
        raise AuthError("Invalid token type.", status_code=401)

    user_id = payload.get("sub")
    jti = payload.get("jti")

    if not user_id or not jti:
        raise AuthError("Malformed token.", status_code=401)

    # Check if this refresh token is still active
    active_key = _active_refresh_key(user_id, jti)
    is_active = await redis.exists(active_key)
    if not is_active:
        logger.warning("Attempted reuse of revoked refresh token: jti=%s user=%s", jti, user_id)
        raise AuthError("Refresh token has been revoked.", status_code=401)

    # Verify user still exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthError("User not found.", status_code=401)

    # Revoke the old refresh token
    await redis.delete(active_key)

    # Mark old refresh token as explicitly revoked (defense in depth)
    revoke_ttl = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
    await redis.set(_revoked_token_key(jti), "1", ex=revoke_ttl)

    # Issue new token pair
    access_token, new_refresh_token, new_access_jti, new_refresh_jti = create_token_pair(
        str(user.id)
    )

    # Register new refresh token
    await redis.set(
        _active_refresh_key(str(user.id), new_refresh_jti),
        "1",
        ex=revoke_ttl,
    )

    logger.info("Token rotation completed for user %s", user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


# --- Logout ---

async def logout_user(redis: Redis, access_token_str: str) -> None:
    """
    Revoke the current access token.

    Stores the token's jti in Redis with a TTL matching the token's remaining
    lifetime. The get_current_user dependency checks this blocklist on every
    request.

    We also attempt to decode and check if there's useful info, but the
    primary mechanism is access token revocation.
    """
    try:
        payload = decode_token(access_token_str)
    except jwt.InvalidTokenError:
        # Token is already invalid — nothing to revoke
        return

    jti = payload.get("jti")
    if not jti:
        return

    # Revoke the access token for its remaining lifetime
    access_ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    await redis.set(_revoked_token_key(jti), "1", ex=access_ttl)

    user_id = payload.get("sub", "unknown")
    logger.info("User %s logged out, access token revoked", user_id)


# --- Token Validation (for get_current_user dependency) ---

async def validate_access_token(db: Session, redis: Redis, token: str) -> User:
    """
    Validate an access token and return the associated user.

    This is the core of the authentication dependency. It:
      1. Decodes the token
      2. Verifies it's an access token
      3. Checks if it's been revoked
      4. Loads the user from the database

    Raises:
        AuthError: If the token is invalid or the user doesn't exist.
    """
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired.", status_code=401)
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token.", status_code=401)

    if payload.get("type") != "access":
        raise AuthError("Invalid token type.", status_code=401)

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not jti or not user_id:
        raise AuthError("Malformed token.", status_code=401)

    # Check revocation
    is_revoked = await redis.exists(_revoked_token_key(jti))
    if is_revoked:
        raise AuthError("Token has been revoked.", status_code=401)

    # Load user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthError("User not found.", status_code=401)

    return user
