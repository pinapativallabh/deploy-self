import uuid
from datetime import datetime
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.deployment import Deployment, DeploymentStatus
from app.models.project import Project
from app.models.user import User
from app.schemas.deployment import DeploymentCreate
from app.services.git_service import GitService
from app.services.docker_service import DockerService
from app.services.project_service import ProjectService


import time
import httpx
import logging
from app.db.session import SessionLocal
from app.core.config import settings

logger = logging.getLogger(__name__)

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
    def trigger_deployment(db: Session, user: User, project_id: uuid.UUID, deployment_in: DeploymentCreate, commit_sha: str = None) -> Deployment:
        # Check permissions first
        project = ProjectService.get_project(db, user, project_id)

        # Lock project to prevent race condition on deployment_number
        project = db.scalar(select(Project).where(Project.id == project_id).with_for_update())

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
        # Note: We do not commit here to ensure the cancellation and new deployment are atomic

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
            commit_sha=commit_sha,
        )
        db.add(deployment)
        
        try:
            db.commit()
            db.refresh(deployment)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A deployment is already being triggered for this project",
            )

        return deployment

    @staticmethod
    def redeploy(db: Session, user: User, project_id: uuid.UUID) -> Deployment:
        project = ProjectService.get_project(db, user, project_id)
        if not project.active_deployment_id:
            raise HTTPException(status_code=400, detail="No active deployment to redeploy")
        
        active_deployment = db.get(Deployment, project.active_deployment_id)
        if not active_deployment:
            raise HTTPException(status_code=400, detail="Active deployment not found")

        return DeploymentService.trigger_deployment(
            db, user, project_id, DeploymentCreate(branch=active_deployment.branch)
        )

    @staticmethod
    def rollback(db: Session, user: User, project_id: uuid.UUID, deployment_id: uuid.UUID) -> Deployment:
        project = ProjectService.get_project(db, user, project_id)
        target_deployment = db.get(Deployment, deployment_id)
        
        if not target_deployment or target_deployment.project_id != project.id:
            raise HTTPException(status_code=404, detail="Target deployment not found")
            
        if target_deployment.status not in [DeploymentStatus.RUNNING, DeploymentStatus.ARCHIVED]:
            raise HTTPException(status_code=400, detail="Can only rollback to successful deployments")

        return DeploymentService.trigger_deployment(
            db, user, project_id, DeploymentCreate(branch=target_deployment.branch), target_deployment.commit_sha
        )

    @staticmethod
    def cleanup_old_deployments(db: Session, project_id: uuid.UUID, active_deployment_id: uuid.UUID = None):
        """Removes successful deployment artifacts beyond the retention limit."""
        # Find all successful deployments ordered by created_at desc
        stmt = (
            select(Deployment)
            .where(
                Deployment.project_id == project_id,
                Deployment.status == DeploymentStatus.RUNNING
            )
            .order_by(Deployment.created_at.desc())
        )
        successful_deployments = db.scalars(stmt).all()
        
        if len(successful_deployments) > settings.CLEANUP_RETENTION:
            for dep_to_remove in successful_deployments[settings.CLEANUP_RETENTION:]:
                if active_deployment_id and dep_to_remove.id == active_deployment_id:
                    continue
                
                # Mark as archived
                dep_to_remove.status = DeploymentStatus.ARCHIVED
                db.commit()

                # Remove container if still somehow exists (though should be stopped)
                old_container_name = f"bonk-{project_id}-{dep_to_remove.deployment_number}"
                DockerService.stop_and_remove_container(old_container_name)

    @staticmethod
    def execute_deployment(deployment_id: uuid.UUID) -> None:
        """
        Background worker method to orchestrate the deployment pipeline.
        """
        with SessionLocal() as db:
            deployment = db.get(Deployment, deployment_id)
            if not deployment or deployment.status != DeploymentStatus.PENDING:
                return
            
            start_time = time.time()

            project = deployment.project
            old_active_deployment_id = project.active_deployment_id

            try:
                # Started
                deployment.status = DeploymentStatus.CLONING
                deployment.started_at = func.now()
                db.commit()

                # Clone
                repo_path, commit_sha = GitService.clone_repo(
                    repository_url=project.repository_url,
                    branch=deployment.branch,
                    project_id=str(project.id),
                    commit_sha=deployment.commit_sha
                )
                deployment.commit_sha = commit_sha
                
                # Building
                deployment.status = DeploymentStatus.BUILDING
                db.commit()

                image_tag = f"bonk-{project.id}:deployment-{deployment.deployment_number}"
                container_name = f"bonk-{project.id}-{deployment.deployment_number}"

                import os
                logs_dir = os.path.join("storage", "logs", "deployments")
                os.makedirs(logs_dir, exist_ok=True)
                log_file_path = os.path.join(logs_dir, f"{deployment.id}.log")

                from app.services.docker_service import DockerServiceBuildException
                try:
                    image_tag, build_logs = DockerService.build_image(
                        repo_path=repo_path,
                        image_tag=image_tag,
                        build_context=project.build_context,
                        dockerfile_path=project.dockerfile_path
                    )
                    with open(log_file_path, "w", encoding="utf-8") as f:
                        f.write(build_logs)
                    deployment.logs_path = log_file_path
                    db.commit()
                except DockerServiceBuildException as e:
                    with open(log_file_path, "w", encoding="utf-8") as f:
                        f.write(e.logs)
                    deployment.logs_path = log_file_path
                    db.commit()
                    raise e

                # Starting
                deployment.status = DeploymentStatus.STARTING
                db.commit()

                from app.services.environment_service import EnvironmentService
                env_vars = EnvironmentService.get_deployment_variables(db, project.id)

                _ = DockerService.run_container(
                    image_tag=image_tag,
                    container_name=container_name,
                    env_vars=env_vars
                )

                # Health Check
                if project.health_check_path:
                    # Give it a tiny bit of time to register ports
                    time.sleep(2)
                    ports = DockerService.get_container_ports(container_name)
                    if not ports:
                        DockerService.stop_container(container_name)
                        raise RuntimeError("Container exposes no ports for health check")
                    
                    host_port = list(ports.values())[0]
                    health_url = f"http://host.docker.internal:{host_port}{project.health_check_path}"
                    
                    is_healthy = False
                    for _ in range(settings.HEALTH_CHECK_TIMEOUT):
                        try:
                            r = httpx.get(health_url, timeout=2.0)
                            if r.status_code == 200:
                                is_healthy = True
                                break
                        except httpx.RequestError:
                            pass
                        time.sleep(settings.POLLING_INTERVAL)
                        
                    if not is_healthy:
                        DockerService.stop_container(container_name)
                        raise RuntimeError(f"Health check failed or timed out after {settings.HEALTH_CHECK_TIMEOUT}s")

                # Healthy/Running
                deployment.status = DeploymentStatus.RUNNING
                deployment.finished_at = func.now()
                
                project.active_deployment_id = deployment.id
                db.commit()

                # Cleanup previous container if it exists
                if old_active_deployment_id and old_active_deployment_id != deployment.id:
                    old_deployment = db.get(Deployment, old_active_deployment_id)
                    if old_deployment:
                        old_container_name = f"bonk-{project.id}-{old_deployment.deployment_number}"
                        DockerService.stop_and_remove_container(old_container_name)

                duration = time.time() - start_time
                logger.info(f"Deployment succeeded | deployment_id={deployment.id} project_id={project.id} status={deployment.status} duration={duration:.2f}s")

                DeploymentService.cleanup_old_deployments(db, project.id, project.active_deployment_id)
                DockerService.prune_resources()

            except Exception as e:
                db.rollback()
                deployment = db.get(Deployment, deployment_id)
                deployment.status = DeploymentStatus.FAILED
                deployment.error_message = str(e)
                deployment.finished_at = func.now()
                db.commit()

                duration = time.time() - start_time
                logger.error(f"Deployment failed | deployment_id={deployment.id} project_id={deployment.project_id} status={deployment.status} duration={duration:.2f}s error='{str(e)}'")
                
                failed_container_name = f"bonk-{deployment.project_id}-{deployment.deployment_number}"
                DockerService.stop_and_remove_container(failed_container_name)
