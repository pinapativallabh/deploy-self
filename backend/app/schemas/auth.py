"""
Authentication request and response schemas.

WHY SEPARATE FROM THE ORM MODEL:
Pydantic schemas define the API contract — what the client sends and receives.
ORM models define the database structure. Coupling them means database changes
break the API contract. Keeping them separate lets us evolve each independently.

WHY PASSWORD CONFIRMATION IN THE SCHEMA:
Validating password_confirm == password at the schema level means the service
layer never sees unconfirmed passwords. This is a validation concern, not
business logic, so it belongs in the schema.

WHY EMAIL NORMALIZATION:
Email addresses are case-insensitive per RFC 5321. "User@Example.COM" and
"user@example.com" are the same mailbox. Normalizing to lowercase on input
prevents duplicate accounts and case-sensitive lookup failures.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    """User registration payload."""

    email: EmailStr = Field(
        ...,
        max_length=320,
        examples=["user@example.com"],
        description="Email address. Will be normalized to lowercase.",
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
        examples=["deploy_user"],
        description="Username. Alphanumeric, underscores, and hyphens only.",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["strongpassword123"],
        description="Password. Minimum 8 characters.",
    )
    password_confirm: str = Field(
        ...,
        examples=["strongpassword123"],
        description="Must match password.",
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Lowercase the entire email address for consistent storage and lookup."""
        return v.strip().lower()

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, v: str) -> str:
        """Strip whitespace from username."""
        return v.strip()

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        """Ensure password and password_confirm are identical."""
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    """Login payload. Accepts email or username."""

    login: str = Field(
        ...,
        min_length=3,
        max_length=320,
        examples=["user@example.com"],
        description="Email address or username.",
    )
    password: str = Field(
        ...,
        examples=["strongpassword123"],
        description="Account password.",
    )

    @field_validator("login", mode="before")
    @classmethod
    def normalize_login(cls, v: str) -> str:
        """Lowercase and strip the login identifier for consistent lookup."""
        return v.strip().lower()


class RefreshRequest(BaseModel):
    """Token refresh payload."""

    refresh_token: str = Field(
        ...,
        description="The refresh token issued during login.",
    )


class TokenResponse(BaseModel):
    """JWT token pair returned after successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user representation. Never includes password_hash."""

    id: uuid.UUID
    email: str
    username: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Generic message response for operations like logout."""

    message: str
