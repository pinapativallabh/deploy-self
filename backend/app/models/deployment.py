import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DeploymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CLONING = "CLONING"
    BUILDING = "BUILDING"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    ARCHIVED = "ARCHIVED"


class Deployment(Base):
    __tablename__ = "deployments"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "deployment_number",
            name="uq_deployments_project_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    deployment_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus),
        nullable=False,
        default=DeploymentStatus.PENDING,
    )

    branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    commit_message: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    logs_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    host_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    deployment_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="deployments",
        foreign_keys=[project_id],
    )

    @property
    def is_active(self) -> bool:
        return self.project.active_deployment_id == self.id if self.project else False

    @property
    def duration(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def __repr__(self) -> str:
        return f"<Deployment #{self.deployment_number} {self.id}>"
