"""
Project model.

A Project is the root business entity of Bonk. It represents a deployable
application definition—not a deployment, container, or running service.

Future entities such as Deployments, Environment Variables, Logs, and Runtime
Status will all belong to a Project.
"""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Project(Base):
    __tablename__ = "projects"

    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "name",
            name="uq_projects_owner_name",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    repository_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    default_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default="main",
    )

    dockerfile_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default="Dockerfile",
    )

    build_context: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default=".",
    )

    health_check_path: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default="/health",
    )

    active_deployment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployments.id", ondelete="SET NULL", use_alter=True, name="fk_active_deployment"),
        nullable=True,
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

    owner: Mapped["User"] = relationship(
        back_populates="projects",
    )

    deployments: Mapped[List["Deployment"]] = relationship(
        "Deployment",
        back_populates="project",
        foreign_keys="[Deployment.project_id]",
        cascade="all, delete-orphan",
    )

    environment_variables: Mapped[List["EnvironmentVariable"]] = relationship(
        "EnvironmentVariable",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    active_deployment: Mapped["Deployment"] = relationship(
        "Deployment",
        foreign_keys=[active_deployment_id],
        post_update=True,
    )

    def __repr__(self) -> str:
        return f"<Project {self.name} ({self.id})>"