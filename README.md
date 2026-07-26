# Bonk

Bonk is a self-hosted control plane for building and running applications from Git repositories on infrastructure you operate. It provides authenticated project management, deployment history, build logs, runtime controls, and rollback support.

## Architecture

```text
Next.js frontend -> FastAPI API -> PostgreSQL
                                  -> Redis / ARQ -> deployment worker
                                                   -> host Docker daemon
```

The API records deployment state in PostgreSQL and queues work in Redis. The ARQ worker clones the configured repository, builds an image, starts the resulting container, and promotes it only after its health check succeeds.

## Requirements

- Docker Engine with Docker Compose
- Git

## Quick start

```bash
git clone https://github.com/pinapativallabh/deploy-self.git bonk
cd bonk
cp backend/.env.example backend/.env
docker compose up --build -d
```

Open `http://localhost:3000/login`. The API health endpoint is available at `http://localhost:8000/health`.

The Compose configuration runs Alembic migrations before starting the API and waits for PostgreSQL, Redis, and API health checks before dependent services start.

## Configuration

Backend settings are loaded from `backend/.env`; use `backend/.env.example` as the template. For deployment outside local development:

- Set a unique, high-entropy `JWT_SECRET_KEY`.
- Set `APP_ENV` to a non-development value. The application rejects its generated development JWT secret in this mode.
- Set `CORS_ORIGINS` to a JSON array of trusted frontend origins.
- Replace the development PostgreSQL password.

Do not commit environment files or mount the Docker socket into an untrusted deployment. The deployment worker requires Docker daemon access and can build and run user-configured repositories.

## Development and verification

```bash
# Frontend
cd frontend
npm ci
npm run lint
npm run build

# Full stack, from the repository root
docker compose up --build -d
docker compose exec backend alembic current
docker compose ps
```

## API highlights

- `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`
- `GET|POST /projects`
- `POST /projects/{project_id}/deployments`
- `POST /projects/{project_id}/redeploy`
- `POST /projects/{project_id}/rollback/{deployment_id}`
- `GET /projects/{project_id}/logs`
- `GET /health`

Interactive API documentation is available at `http://localhost:8000/docs` while the API is running.

## Migrations

Run Alembic commands from `backend/`:

```bash
alembic upgrade head
alembic current
```

Review generated migrations before committing them. Production migrations are applied automatically by the backend Compose service.
