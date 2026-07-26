# Bonk Architecture

## System Architecture
Bonk is an autonomous platform for deploying web applications, similar to Heroku or Vercel. 
It uses a FastAPI backend, a PostgreSQL database for state and metadata, a Redis instance for message brokering and caching, and a containerized environment (Docker) to build and run deployments.

- **Backend:** FastAPI (Python), providing the RESTful API for users to create and manage projects, environment variables, and trigger deployments.
- **Database:** PostgreSQL storing `User`, `Project`, `Deployment`, and `EnvironmentVariable`.
- **Cache/Broker:** Redis, used by ARQ for deployment job queuing and token revocation.
- **Worker/Deployment Engine:** An ARQ worker orchestrates Docker directly (using `docker-py`) to build images and run deployments.

## Request Flow
1. User authenticates via `/auth/login` and receives a JWT token.
2. User creates a Project via `POST /projects/`, providing a repository URL and build settings.
3. User adds environment variables via `POST /projects/{project_id}/environment/`.
4. User triggers a deployment via `POST /projects/{project_id}/deployments/`.
5. The API enqueues the deployment or executes it asynchronously using `execute_deployment()`.

## Deployment Lifecycle
1. **PENDING**: Deployment is queued.
2. **CLONING**: The Git service clones the repository locally or fetches updates to reuse the cache.
3. **BUILDING**: Docker service builds an image using the specified `dockerfile_path` and `build_context`.
4. **STARTING**: Docker service runs the container, injecting environment variables.
5. **RUNNING**: The container is healthy. The previous active container is stopped and removed.
6. **FAILED**: If any step fails, the deployment is marked as failed, and logs are captured.
7. **CANCELED**: When a new deployment supersedes a pending one, the older one is canceled.

## Major Services
- **AuthService**: Handles user registration, login, and JWT generation/validation.
- **ProjectService**: Manages project metadata.
- **EnvironmentService**: Manages environment variables (with secret masking).
- **GitService**: Handles cloning and caching repositories locally using `git reset --hard` and `git clean -fdx` for consistency.
- **DockerService**: Wrapper around Docker SDK to build images, run containers, and manage resources. Includes prune mechanisms to clean up orphaned containers and dangling images.
- **DeploymentService**: Orchestrates the entire deployment lifecycle, linking Git cloning, Docker building, health checks, and database status updates. Includes rollback and redeployment logic.

## Database Relationships
- `User` 1:N `Project`
- `Project` 1:N `Deployment`
- `Project` 1:N `EnvironmentVariable`

## Design Decisions
- **Docker in Docker / SDK**: To keep the MVP simple, the backend uses `docker-py` to orchestrate containers on the host daemon (by mounting the docker socket).
- **Local Repo Cache**: Repositories are cloned to a persistent `repos/` cache path. Subsequent deployments reuse the cache to speed up the process.
- **Explicit Dependency Health Check**: `/health` endpoint checks Postgres and Redis separately to aid ops debugging.
- **Pydantic Settings**: Centralized configuration management using `.env` variables with strict typing.
