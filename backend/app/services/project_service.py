import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    """
    Business service for managing Projects.
    Handles business rules, database operations, and error raising.
    """

    @staticmethod
    def _get_project_by_name(db: Session, owner_id: uuid.UUID, name: str) -> Project | None:
        """Helper to fetch a project by name for a specific owner."""
        stmt = select(Project).where(Project.owner_id == owner_id, Project.name == name)
        return db.scalar(stmt)

    @staticmethod
    def _enforce_unique_name(db: Session, owner_id: uuid.UUID, name: str) -> None:
        """Raises 409 Conflict if a project with the given name already exists for the owner."""
        if ProjectService._get_project_by_name(db, owner_id, name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with name '{name}' already exists for this user.",
            )

    @staticmethod
    def create_project(db: Session, user: User, project_in: ProjectCreate) -> Project:
        ProjectService._enforce_unique_name(db, user.id, project_in.name)

        project = Project(
            owner_id=user.id,
            name=project_in.name,
            description=project_in.description,
            repository_url=project_in.repository_url,
            default_branch=project_in.default_branch,
            dockerfile_path=project_in.dockerfile_path,
            build_context=project_in.build_context,
            health_check_path=project_in.health_check_path,
        )
        
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_projects(db: Session, user: User) -> Sequence[Project]:
        stmt = select(Project).where(Project.owner_id == user.id)
        return db.scalars(stmt).all()

    @staticmethod
    def get_project(db: Session, user: User, project_id: uuid.UUID) -> Project:
        project = db.get(Project, project_id)
        if not project or project.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    @staticmethod
    def update_project(
        db: Session, user: User, project_id: uuid.UUID, project_in: ProjectUpdate
    ) -> Project:
        project = ProjectService.get_project(db, user, project_id)
        
        update_data = project_in.model_dump(exclude_unset=True)
        
        if "name" in update_data and update_data["name"] != project.name:
            ProjectService._enforce_unique_name(db, user.id, update_data["name"])
            
        for field, value in update_data.items():
            setattr(project, field, value)
            
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete_project(db: Session, user: User, project_id: uuid.UUID) -> None:
        project = ProjectService.get_project(db, user, project_id)
        db.delete(project)
        db.commit()
