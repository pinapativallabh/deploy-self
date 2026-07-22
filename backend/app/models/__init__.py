"""
Models package.

All ORM models are imported here so that:
  1. Alembic's autogenerate can discover them via Base.metadata
  2. Other modules can import from app.models directly

Every new model MUST be imported in this file or Alembic will not detect it.
"""

from .user import User
from .project import Project

__all__ = [
    "User",
    "Project",
]