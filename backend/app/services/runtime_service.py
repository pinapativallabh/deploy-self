import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project
from app.services.docker_service import DockerService, DockerServiceException


class RuntimeService:
    @staticmethod
    def _get_active_container_name(db: Session, project_id: uuid.UUID) -> str:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if not project.active_deployment_id:
            raise HTTPException(status_code=404, detail="Project has no active deployment")
        
        deployment = project.active_deployment
        return f"bonk-{project.id}-{deployment.deployment_number}"

    @staticmethod
    def get_status(db: Session, project_id: uuid.UUID) -> dict:
        container_name = RuntimeService._get_active_container_name(db, project_id)
        try:
            status = DockerService.get_container_status(container_name)
            return {"status": status}
        except DockerServiceException as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def restart(db: Session, project_id: uuid.UUID) -> dict:
        container_name = RuntimeService._get_active_container_name(db, project_id)
        try:
            DockerService.restart_container(container_name)
            return {"status": "restarted"}
        except DockerServiceException as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def stop(db: Session, project_id: uuid.UUID) -> dict:
        container_name = RuntimeService._get_active_container_name(db, project_id)
        try:
            DockerService.stop_container(container_name)
            return {"status": "stopped"}
        except DockerServiceException as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def start(db: Session, project_id: uuid.UUID) -> dict:
        container_name = RuntimeService._get_active_container_name(db, project_id)
        try:
            DockerService.start_container(container_name)
            return {"status": "started"}
        except DockerServiceException as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def remove(db: Session, project_id: uuid.UUID) -> dict:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not project.active_deployment_id:
            return {"status": "already_removed"}
        
        deployment = project.active_deployment
        container_name = f"bonk-{project.id}-{deployment.deployment_number}"
        
        try:
            DockerService.remove_container(container_name)
            # Unset active deployment since runtime is gone
            project.active_deployment_id = None
            db.commit()
            return {"status": "removed"}
        except DockerServiceException as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def _get_target_deployment(db: Session, project_id: uuid.UUID, deployment_id: Optional[uuid.UUID] = None):
        from app.models.deployment import Deployment
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if deployment_id:
            deployment = db.get(Deployment, deployment_id)
            if not deployment or deployment.project_id != project.id:
                raise HTTPException(status_code=404, detail="Deployment not found")
        else:
            deployment = project.active_deployment
            if not deployment:
                raise HTTPException(status_code=404, detail="Project has no active deployment")
        return project, deployment

    @staticmethod
    def _get_build_logs(deployment) -> str:
        build_logs = ""
        if deployment.logs_path:
            import os
            if os.path.exists(deployment.logs_path):
                with open(deployment.logs_path, "r", encoding="utf-8") as f:
                    build_logs = f.read()
        return build_logs

    @staticmethod
    def get_logs(db: Session, project_id: uuid.UUID, deployment_id: Optional[uuid.UUID] = None, tail: str | int = "all", timestamps: bool = False) -> dict:
        project, deployment = RuntimeService._get_target_deployment(db, project_id, deployment_id)
        build_logs = RuntimeService._get_build_logs(deployment)
        container_name = f"bonk-{project.id}-{deployment.deployment_number}"
        
        runtime_logs = ""
        try:
            runtime_logs = DockerService.tail_logs(container_name, tail=tail, timestamps=timestamps)
        except DockerServiceException:
            pass

        return {
            "build_logs": build_logs,
            "runtime_logs": runtime_logs
        }

    @staticmethod
    def stream_logs(db: Session, project_id: uuid.UUID, deployment_id: Optional[uuid.UUID] = None, tail: str | int = "all", timestamps: bool = False):
        project, deployment = RuntimeService._get_target_deployment(db, project_id, deployment_id)
        container_name = f"bonk-{project.id}-{deployment.deployment_number}"
        
        try:
            return DockerService.stream_logs(container_name, tail=tail, timestamps=timestamps)
        except DockerServiceException as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def tail_logs(db: Session, project_id: uuid.UUID, deployment_id: Optional[uuid.UUID] = None, tail: int = 100, timestamps: bool = False) -> dict:
        return RuntimeService.get_logs(db, project_id, deployment_id, tail=tail, timestamps=timestamps)

    @staticmethod
    def inspect(db: Session, project_id: uuid.UUID) -> dict:
        container_name = RuntimeService._get_active_container_name(db, project_id)
        try:
            info = DockerService.inspect_container(container_name)
            return info
        except DockerServiceException as e:
            raise HTTPException(status_code=500, detail=str(e))
