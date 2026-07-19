"""
Security primitives: password hashing and JWT management.

WHY THIS MODULE EXISTS:
Security operations (hashing, token signing) are infrastructure concerns that
multiple services may need. Centralizing them here avoids scattered crypto code
and ensures consistent algorithm choices.

WHY ARGON2ID:
Argon2id is the winner of the Password Hashing Competition and is recommended
by OWASP as the primary choice for password hashing. It provides resistance
against both GPU-based attacks (memory-hard) and side-channel attacks (data-
independent memory access). bcrypt is a solid alternative but Argon2id is
the modern standard.

WHY pwdlib:
pwdlib is a modern, lightweight password hashing library that provides a clean
interface for Argon2 hashing. It wraps argon2-cffi and provides a simple
verify-and-update pattern. It's the recommended library for new FastAPI projects
as passlib is no longer actively maintained.

WHY JTI (JWT ID):
Each token gets a unique identifier (jti). This enables token revocation: when
a user logs out or a refresh token is rotated, we store the jti in Redis. On
subsequent requests, we check if the jti has been revoked. Without jti, there's
no way to invalidate individual tokens before expiry.

WHY SEPARATE ACCESS AND REFRESH TOKENS:
Access tokens are short-lived (15 min) and sent with every API request. If
compromised, the damage window is small. Refresh tokens are long-lived (7 days)
but only sent to the /auth/refresh endpoint. This separation limits exposure:
an intercepted access token expires quickly, and the refresh token is never
sent to arbitrary endpoints.
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings

logger = logging.getLogger("app.security")

# --- Password Hashing ---

password_hasher = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its Argon2id hash.

    Returns True if the password matches, False otherwise.
    Never raises on wrong passwords — timing-safe comparison is handled
    internally by the Argon2 library.
    """
    return password_hasher.verify(plain_password, hashed_password)


# --- JWT Tokens ---


def create_access_token(user_id: str, jti: str | None = None) -> str:
    """
    Create a short-lived JWT access token.

    Args:
        user_id: The user's UUID as a string.
        jti: Optional JWT ID. Generated if not provided.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    jti = jti or str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "type": "access",
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, jti: str | None = None) -> str:
    """
    Create a long-lived JWT refresh token.

    Args:
        user_id: The user's UUID as a string.
        jti: Optional JWT ID. Generated if not provided.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    jti = jti or str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is malformed or signature is invalid.

    Returns:
        The decoded payload as a dictionary.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


def create_token_pair(user_id: str) -> tuple[str, str, str, str]:
    """
    Create a matched access + refresh token pair.

    Returns:
        Tuple of (access_token, refresh_token, access_jti, refresh_jti).
        The jtis are returned so the caller can store them for revocation.
    """
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())

    access_token = create_access_token(user_id, jti=access_jti)
    refresh_token = create_refresh_token(user_id, jti=refresh_jti)

    return access_token, refresh_token, access_jti, refresh_jti
