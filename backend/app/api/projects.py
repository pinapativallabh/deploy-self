import uuid
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
from app.services.project_service import ProjectService
from app.services.deployment_service import DeploymentService
from fastapi import BackgroundTasks

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """
    Create a new project.
    """
    return ProjectService.create_project(db=db, user=current_user, project_in=project_in)


@router.get(
    "",
    response_model=List[ProjectResponse],
    summary="List projects",
)
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ProjectResponse]:
    """
    Retrieve all projects owned by the current user.
    """
    return ProjectService.get_projects(db=db, user=current_user)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project",
)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """
    Retrieve a project by ID.
    """
    return ProjectService.get_project(db=db, user=current_user, project_id=project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
)
def update_project(
    project_id: uuid.UUID,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectResponse:
    """
    Update a project's details.
    """
    return ProjectService.update_project(
        db=db, user=current_user, project_id=project_id, project_in=project_in
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Delete a project.
    """
    ProjectService.delete_project(db=db, user=current_user, project_id=project_id)


@router.post(
    "/{project_id}/deployments",
    response_model=DeploymentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a deployment",
)
def trigger_deployment(
    project_id: uuid.UUID,
    deployment_in: DeploymentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeploymentResponse:
    """
    Trigger a new deployment for a project.
    Executes asynchronously.
    """
    deployment = DeploymentService.trigger_deployment(
        db=db, user=current_user, project_id=project_id, deployment_in=deployment_in
    )
    
    # Run the orchestrator in the background
    background_tasks.add_task(
        DeploymentService.execute_deployment,
        deployment_id=deployment.id
    )
    
    return deployment


@router.get(
    "/{project_id}/deployments",
    response_model=List[DeploymentResponse],
    summary="List deployments",
)
def list_deployments(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[DeploymentResponse]:
    """
    Retrieve all deployments for a project.
    """
    return DeploymentService.get_deployments(db=db, user=current_user, project_id=project_id)


@router.get(
    "/{project_id}/deployments/{deployment_id}",
    response_model=DeploymentResponse,
    summary="Get deployment",
)
def get_deployment(
    project_id: uuid.UUID,
    deployment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DeploymentResponse:
    """
    Retrieve a specific deployment.
    """
    return DeploymentService.get_deployment(
        db=db, user=current_user, project_id=project_id, deployment_id=deployment_id
    )
