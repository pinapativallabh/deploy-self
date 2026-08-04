import uuid
import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


from app.core.config import settings

class EnvironmentVariableBase(BaseModel):
    key: str = Field(..., max_length=255, strip_whitespace=True)
    value: str = Field(..., max_length=settings.MAX_ENV_VAR_SIZE, strip_whitespace=True)
    is_secret: bool = Field(default=False)

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Key cannot be empty")
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError("Invalid environment variable name")
        return v


class EnvironmentVariableCreate(EnvironmentVariableBase):
    pass


class EnvironmentVariableUpdate(BaseModel):
    key: Optional[str] = Field(None, max_length=255, strip_whitespace=True)
    value: Optional[str] = Field(None, max_length=settings.MAX_ENV_VAR_SIZE, strip_whitespace=True)
    is_secret: Optional[bool] = None

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v:
                raise ValueError("Key cannot be empty")
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
                raise ValueError("Invalid environment variable name")
        return v


class EnvironmentVariableResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    key: str
    value: str
    is_secret: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def mask_secret_value(self) -> "EnvironmentVariableResponse":
        if self.is_secret:
            self.value = "********"
        return self
