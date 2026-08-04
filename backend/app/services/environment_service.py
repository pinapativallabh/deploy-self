import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.environment_variable import EnvironmentVariable
from app.models.user import User
from app.schemas.environment_variable import EnvironmentVariableCreate, EnvironmentVariableUpdate
from app.services.project_service import ProjectService


class EnvironmentService:
    @staticmethod
    def get_variables(db: Session, user: User, project_id: uuid.UUID) -> Sequence[EnvironmentVariable]:
        project = ProjectService.get_project(db, user, project_id)
        
        stmt = select(EnvironmentVariable).where(
            EnvironmentVariable.project_id == project.id
        ).order_by(EnvironmentVariable.key)
        return db.scalars(stmt).all()

    @staticmethod
    def create_variable(
        db: Session, user: User, project_id: uuid.UUID, variable_in: EnvironmentVariableCreate
    ) -> EnvironmentVariable:
        project = ProjectService.get_project(db, user, project_id)
        
        from app.core.config import settings
        count = db.scalar(select(func.count(EnvironmentVariable.id)).where(EnvironmentVariable.project_id == project.id))
        if count >= settings.MAX_ENV_VARS_PER_PROJECT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum number of environment variables ({settings.MAX_ENV_VARS_PER_PROJECT}) reached for this project",
            )
        
        variable = EnvironmentVariable(
            project_id=project.id,
            key=variable_in.key,
            value=variable_in.value,
            is_secret=variable_in.is_secret,
        )
        db.add(variable)
        try:
            db.commit()
            db.refresh(variable)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Environment variable with key '{variable_in.key}' already exists for this project",
            )
            
        return variable

    @staticmethod
    def get_variable(db: Session, user: User, project_id: uuid.UUID, variable_id: uuid.UUID) -> EnvironmentVariable:
        project = ProjectService.get_project(db, user, project_id)
        
        variable = db.get(EnvironmentVariable, variable_id)
        if not variable or variable.project_id != project.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment variable not found",
            )
        return variable

    @staticmethod
    def update_variable(
        db: Session, user: User, project_id: uuid.UUID, variable_id: uuid.UUID, variable_in: EnvironmentVariableUpdate
    ) -> EnvironmentVariable:
        variable = EnvironmentService.get_variable(db, user, project_id, variable_id)
        
        update_data = variable_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(variable, field, value)
            
        try:
            db.commit()
            db.refresh(variable)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Environment variable with key '{variable_in.key}' already exists for this project",
            )
            
        return variable

    @staticmethod
    def delete_variable(db: Session, user: User, project_id: uuid.UUID, variable_id: uuid.UUID) -> None:
        variable = EnvironmentService.get_variable(db, user, project_id, variable_id)
        
        db.delete(variable)
        db.commit()

    @staticmethod
    def get_deployment_variables(db: Session, project_id: uuid.UUID) -> dict[str, str]:
        """
        Internal method for DeploymentService to fetch env vars for a project.
        """
        stmt = select(EnvironmentVariable).where(EnvironmentVariable.project_id == project_id)
        variables = db.scalars(stmt).all()
        
        return {var.key: var.value for var in variables}
