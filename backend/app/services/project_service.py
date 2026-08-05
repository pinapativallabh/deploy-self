import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

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
    def _generate_slug(db: Session, name: str) -> str:
        import re
        import random
        import string
        
        base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        if not base_slug:
            base_slug = "app"
            
        slug = base_slug
        while db.scalar(select(Project).where(Project.slug == slug)):
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
            slug = f"{base_slug}-{suffix}"
            
        return slug

    @staticmethod
    def create_project(db: Session, user: User, project_in: ProjectCreate) -> Project:
        ProjectService._enforce_unique_name(db, user.id, project_in.name)

        slug = ProjectService._generate_slug(db, project_in.name)

        project = Project(
            owner_id=user.id,
            name=project_in.name,
            slug=slug,
            description=project_in.description,
            repository_url=project_in.repository_url,
            default_branch=project_in.default_branch,
            dockerfile_path=project_in.dockerfile_path,
            build_context=project_in.build_context,
            health_check_path=project_in.health_check_path,
        )
        
        db.add(project)
        try:
            db.commit()
            db.refresh(project)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with name '{project_in.name}' already exists for this user.",
            )
        return project

    @staticmethod
    def get_projects(db: Session, user: User) -> Sequence[Project]:
        from sqlalchemy.orm import joinedload
        stmt = (
            select(Project)
            .where(Project.owner_id == user.id)
            .options(joinedload(Project.active_deployment))
        )
        projects = list(db.scalars(stmt).unique().all())
        
        def get_sort_key(p: Project):
            if p.active_deployment and hasattr(p.active_deployment.created_at, 'timestamp'):
                return p.active_deployment.created_at.timestamp()
            return 0
            
        projects.sort(key=get_sort_key, reverse=True)
        
        from app.services.docker_service import DockerService
        try:
            client = DockerService._get_client()
            containers = client.containers.list(all=True, filters={"name": "bonk-"})
            container_status_map = {c.name: c.status for c in containers}
        except Exception:
            container_status_map = {}
            
        for p in projects:
            p.container_status = None
            if p.active_deployment_id and p.active_deployment:
                c_name = f"bonk-{p.id}-{p.active_deployment.deployment_number}"
                p.container_status = container_status_map.get(c_name)
                
        return projects

    @staticmethod
    def get_project(db: Session, user: User, project_id: uuid.UUID) -> Project:
        from sqlalchemy.orm import joinedload
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(joinedload(Project.active_deployment))
        )
        project = db.scalar(stmt)
        if not project or project.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
            
        from app.services.docker_service import DockerService
        try:
            client = DockerService._get_client()
            if project.active_deployment_id and project.active_deployment:
                c_name = f"bonk-{project.id}-{project.active_deployment.deployment_number}"
                containers = client.containers.list(all=True, filters={"name": c_name})
                project.container_status = containers[0].status if containers else None
            else:
                project.container_status = None
        except Exception:
            project.container_status = None
            
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
            
        try:
            db.commit()
            db.refresh(project)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project with this name already exists for this user.",
            )
        return project

    @staticmethod
    def delete_project(db: Session, user: User, project_id: uuid.UUID) -> None:
        project = ProjectService.get_project(db, user, project_id)
        
        # Cleanup docker resources
        from app.services.docker_service import DockerService
        DockerService.cleanup_project_resources(str(project.id))
        
        # Cleanup git repository cache
        from app.services.git_service import GitService
        GitService.delete_repo(str(project.id))
        
        # Cleanup NGINX configuration
        from app.services.nginx_service import NginxService
        NginxService.remove_deployment(project.slug)
        
        db.delete(project)
        db.commit()
