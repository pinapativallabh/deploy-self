from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.config import settings

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=settings.MAX_PROJECT_NAME_LENGTH, strip_whitespace=True)
    description: Optional[str] = None
    repository_url: str = Field(..., min_length=1, max_length=settings.MAX_REPO_URL_LENGTH, strip_whitespace=True)
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

    @field_validator("dockerfile_path", "build_context")
    @classmethod
    def prevent_path_traversal(cls, v: str) -> str:
        if ".." in v or v.startswith("/"):
            raise ValueError("Path traversal or absolute paths are not allowed")
        return v

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://") or v.startswith("git@")):
            raise ValueError("Repository URL must be a valid HTTP/HTTPS or SSH URL")
        return v


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=settings.MAX_PROJECT_NAME_LENGTH, strip_whitespace=True)
    description: Optional[str] = None
    repository_url: Optional[str] = Field(None, min_length=1, max_length=settings.MAX_REPO_URL_LENGTH, strip_whitespace=True)
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

    @field_validator("dockerfile_path", "build_context")
    @classmethod
    def prevent_path_traversal(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (".." in v or v.startswith("/")):
            raise ValueError("Path traversal or absolute paths are not allowed")
        return v

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not (v.startswith("http://") or v.startswith("https://") or v.startswith("git@")):
            raise ValueError("Repository URL must be a valid HTTP/HTTPS or SSH URL")
        return v


class ProjectResponse(ProjectBase):
    id: UUID
    owner_id: UUID
    active_deployment_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    container_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
