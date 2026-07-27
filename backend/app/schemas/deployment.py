from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.deployment import DeploymentStatus


class DeploymentCreate(BaseModel):
    branch: Optional[str] = Field(None, max_length=255, description="Branch to deploy. If omitted, uses project default.")


class DeploymentResponse(BaseModel):
    id: UUID
    project_id: UUID
    deployment_number: int
    status: DeploymentStatus
    branch: str
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None
    logs_path: Optional[str] = None
    host_port: Optional[int] = None
    deployment_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = False
    duration: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
