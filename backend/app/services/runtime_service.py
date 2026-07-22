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
    def get_logs(db: Session, project_id: uuid.UUID) -> dict:
        container_name = RuntimeService._get_active_container_name(db, project_id)
        try:
            logs = DockerService.get_container_logs(container_name)
            return {"logs": logs}
        except DockerServiceException as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def inspect(db: Session, project_id: uuid.UUID) -> dict:
        container_name = RuntimeService._get_active_container_name(db, project_id)
        try:
            info = DockerService.inspect_container(container_name)
            return info
        except DockerServiceException as e:
            raise HTTPException(status_code=500, detail=str(e))
