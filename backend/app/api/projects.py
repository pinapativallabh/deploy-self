import uuid
from typing import List

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.deployment import DeploymentCreate, DeploymentResponse
from app.schemas.environment_variable import EnvironmentVariableCreate, EnvironmentVariableResponse, EnvironmentVariableUpdate
from app.services.project_service import ProjectService
from app.services.deployment_service import DeploymentService
from app.services.runtime_service import RuntimeService
from app.services.environment_service import EnvironmentService

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


@router.get("/{project_id}/runtime")
def get_runtime_status(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    status = RuntimeService.get_status(db, project_id)
    inspect = RuntimeService.inspect(db, project_id)
    return {"status": status["status"], "inspect": inspect}


from fastapi import Query
from fastapi.responses import StreamingResponse

@router.get("/{project_id}/logs")
def get_runtime_logs(
    project_id: uuid.UUID,
    deployment_id: uuid.UUID = Query(None, description="Optional deployment ID"),
    tail: str = Query("all", description="Number of lines to show from the end of the logs"),
    follow: bool = Query(False, description="Stream the logs"),
    timestamps: bool = Query(False, description="Show timestamps"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if follow:
        iterator = RuntimeService.stream_logs(db, project_id, deployment_id, tail=tail, timestamps=timestamps)
        def generate():
            for chunk in iterator:
                yield chunk
        return StreamingResponse(generate(), media_type="text/plain")
    else:
        return RuntimeService.get_logs(db, project_id, deployment_id, tail=tail, timestamps=timestamps)


@router.post("/{project_id}/restart")
def restart_runtime(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return RuntimeService.restart(db, project_id)


@router.post("/{project_id}/stop")
def stop_runtime(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return RuntimeService.stop(db, project_id)


@router.post("/{project_id}/start")
def start_runtime(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return RuntimeService.start(db, project_id)


@router.delete("/{project_id}/runtime")
def remove_runtime(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.get(Project, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return RuntimeService.remove(db, project_id)


@router.post(
    "/{project_id}/environment",
    response_model=EnvironmentVariableResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create environment variable",
)
def create_environment_variable(
    project_id: uuid.UUID,
    variable_in: EnvironmentVariableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvironmentVariableResponse:
    return EnvironmentService.create_variable(db, current_user, project_id, variable_in)


@router.get(
    "/{project_id}/environment",
    response_model=List[EnvironmentVariableResponse],
    summary="List environment variables",
)
def list_environment_variables(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[EnvironmentVariableResponse]:
    return EnvironmentService.get_variables(db, current_user, project_id)


@router.patch(
    "/{project_id}/environment/{variable_id}",
    response_model=EnvironmentVariableResponse,
    summary="Update environment variable",
)
def update_environment_variable(
    project_id: uuid.UUID,
    variable_id: uuid.UUID,
    variable_in: EnvironmentVariableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EnvironmentVariableResponse:
    return EnvironmentService.update_variable(db, current_user, project_id, variable_id, variable_in)


@router.delete(
    "/{project_id}/environment/{variable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete environment variable",
)
def delete_environment_variable(
    project_id: uuid.UUID,
    variable_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    EnvironmentService.delete_variable(db, current_user, project_id, variable_id)