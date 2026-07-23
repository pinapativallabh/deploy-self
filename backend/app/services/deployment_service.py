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
            
        if target_deployment.status not in [DeploymentStatus.RUNNING]:
            # Assuming RUNNING is the state for a completed/successful deployment
            # We also might want to check if it has a commit_sha
            if not target_deployment.commit_sha:
                raise HTTPException(status_code=400, detail="Target deployment does not have a commit SHA")

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

        deployment = Deployment(
            project_id=project.id,
            deployment_number=next_num,
            status=DeploymentStatus.PENDING,
            branch=target_deployment.branch,
            commit_sha=target_deployment.commit_sha
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
        import time
        import httpx
        from app.db.session import SessionLocal
        
        with SessionLocal() as db:
            deployment = db.get(Deployment, deployment_id)
            if not deployment or deployment.status != DeploymentStatus.PENDING:
                return

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
                        raise Exception("Container exposes no ports for health check")
                    
                    host_port = list(ports.values())[0]
                    health_url = f"http://127.0.0.1:{host_port}{project.health_check_path}"
                    
                    is_healthy = False
                    for _ in range(30):
                        try:
                            r = httpx.get(health_url, timeout=2.0)
                            if r.status_code == 200:
                                is_healthy = True
                                break
                        except httpx.RequestError:
                            pass
                        time.sleep(1)
                        
                    if not is_healthy:
                        DockerService.stop_container(container_name)
                        raise Exception("Health check failed or timed out")

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

            except Exception as e:
                db.rollback()
                deployment = db.get(Deployment, deployment_id)
                deployment.status = DeploymentStatus.FAILED
                deployment.error_message = str(e)
                deployment.finished_at = func.now()
                db.commit()
