import uuid
from datetime import datetime
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from app.models.deployment import Deployment, DeploymentStatus
from app.models.project import Project
from app.models.user import User
from app.schemas.deployment import DeploymentCreate
from app.services.git_service import GitService
from app.services.docker_service import DockerService
from app.services.project_service import ProjectService


class DeploymentService:
    @staticmethod
    def get_deployments(db: Session, user: User, project_id: uuid.UUID) -> Sequence[Deployment]:
        project = ProjectService.get_project(db, user, project_id) # ensures ownership
        
        stmt = select(Deployment).where(Deployment.project_id == project.id).order_by(Deployment.created_at.desc())
        return db.scalars(stmt).all()

    @staticmethod
    def get_deployment(db: Session, user: User, project_id: uuid.UUID, deployment_id: uuid.UUID) -> Deployment:
        # ensures ownership
        project = ProjectService.get_project(db, user, project_id)
        
        deployment = db.get(Deployment, deployment_id)
        if not deployment or deployment.project_id != project.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found",
            )
        return deployment

    @staticmethod
    def trigger_deployment(db: Session, user: User, project_id: uuid.UUID, deployment_in: DeploymentCreate) -> Deployment:
        project = ProjectService.get_project(db, user, project_id)

        # Cancel pending/building deployments for this project
        db.execute(
            update(Deployment)
            .where(
                Deployment.project_id == project.id,
                Deployment.status.in_([DeploymentStatus.PENDING, DeploymentStatus.CLONING, DeploymentStatus.BUILDING])
            )
            .values(
                status=DeploymentStatus.CANCELED,
                finished_at=func.now()
            )
        )
        db.commit()

        # Get next deployment number
        max_num = db.scalar(
            select(func.max(Deployment.deployment_number))
            .where(Deployment.project_id == project.id)
        )
        next_num = (max_num or 0) + 1

        branch = deployment_in.branch if deployment_in.branch else project.default_branch

        deployment = Deployment(
            project_id=project.id,
            deployment_number=next_num,
            status=DeploymentStatus.PENDING,
            branch=branch,
        )
        db.add(deployment)
        db.commit()
        db.refresh(deployment)

        return deployment

    @staticmethod
    def execute_deployment(deployment_id: uuid.UUID) -> None:
        """
        Background worker method to orchestrate the deployment pipeline.
        """
        from app.db.session import SessionLocal
        
        with SessionLocal() as db:
            deployment = db.get(Deployment, deployment_id)
            if not deployment or deployment.status != DeploymentStatus.PENDING:
                return

            project = deployment.project

            try:
                # Started
                deployment.status = DeploymentStatus.CLONING
                deployment.started_at = func.now()
                db.commit()

                # Clone
                commit_sha = GitService.clone_repo(project.repository_url, deployment.branch)
                deployment.commit_sha = commit_sha
                
                # Building
                deployment.status = DeploymentStatus.BUILDING
                db.commit()

                image_tag = DockerService.build_image(
                    project_name=project.name,
                    commit_sha=commit_sha,
                    build_context=project.build_context,
                    dockerfile_path=project.dockerfile_path
                )

                # Starting
                deployment.status = DeploymentStatus.STARTING
                db.commit()

                _ = DockerService.run_container(image_tag=image_tag)

                # Healthy/Running (Simulated health check pass)
                deployment.status = DeploymentStatus.RUNNING
                deployment.finished_at = func.now()
                
                project.active_deployment_id = deployment.id

                db.commit()
            except Exception as e:
                db.rollback()
                deployment = db.get(Deployment, deployment_id)
                deployment.status = DeploymentStatus.FAILED
                deployment.error_message = str(e)
                deployment.finished_at = func.now()
                db.commit()
