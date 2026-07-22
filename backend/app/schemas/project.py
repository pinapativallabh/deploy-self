from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    description: Optional[str] = None
    repository_url: str = Field(..., min_length=1, max_length=500, strip_whitespace=True)
    default_branch: str = Field(default="main", min_length=1, max_length=255, strip_whitespace=True)
    dockerfile_path: str = Field(default="Dockerfile", min_length=1, max_length=255, strip_whitespace=True)
    build_context: str = Field(default=".", min_length=1, max_length=255, strip_whitespace=True)
    health_check_path: str = Field(default="/health", min_length=1, max_length=255, strip_whitespace=True)

    @field_validator("health_check_path")
    @classmethod
    def validate_health_check_path(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError('health_check_path must start with "/"')
        return v


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, strip_whitespace=True)
    description: Optional[str] = None
    repository_url: Optional[str] = Field(None, min_length=1, max_length=500, strip_whitespace=True)
    default_branch: Optional[str] = Field(None, min_length=1, max_length=255, strip_whitespace=True)
    dockerfile_path: Optional[str] = Field(None, min_length=1, max_length=255, strip_whitespace=True)
    build_context: Optional[str] = Field(None, min_length=1, max_length=255, strip_whitespace=True)
    health_check_path: Optional[str] = Field(None, min_length=1, max_length=255, strip_whitespace=True)

    @field_validator("health_check_path")
    @classmethod
    def validate_health_check_path(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith("/"):
            raise ValueError('health_check_path must start with "/"')
        return v


class ProjectResponse(ProjectBase):
    id: UUID
    owner_id: UUID
    active_deployment_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
