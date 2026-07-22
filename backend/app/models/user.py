"""
User model.

This is the foundational identity model for the platform. Every authenticated
action traces back to a User row.

WHY UUID INSTEAD OF AUTO-INCREMENT:
UUIDs prevent enumeration attacks (can't guess user IDs by incrementing),
are safe to expose in URLs and logs, and work across distributed systems
without coordination. The tradeoff is slightly larger storage and slower
index lookups, which is negligible for a user table.

WHY server_default FOR TIMESTAMPS:
Using server_default=func.now() pushes timestamp generation to PostgreSQL.
This means timestamps are consistent even if application servers have clock
skew, and bulk inserts via SQL scripts get correct timestamps automatically.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    """Platform user account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    projects: Mapped[list["Project"]] = relationship(
    back_populates="owner",
    cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.id})>"
