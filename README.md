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
cp .env.example backend/.env
docker compose up --build -d
```

Open `http://localhost:3000/login`. The API health endpoint is available at `http://localhost:8000/health`.

The Compose configuration runs Alembic migrations before starting the API and waits for PostgreSQL, Redis, and API health checks before dependent services start.

## Configuration

Backend settings are loaded from `backend/.env`; use the repository `.env.example` as the template. For deployment outside local development:

- Set a unique, high-entropy `JWT_SECRET_KEY`.
- Set `APP_ENV` to a non-development value. The application rejects its generated development JWT secret in this mode.
- Set `CORS_ORIGINS` to a JSON array of trusted frontend origins.
- Replace the development PostgreSQL password.
- Set `NEXT_PUBLIC_API_URL` to the public URL of the backend (e.g., `http://<your-server-ip>:8000`). This value is baked into the frontend at build time:
  ```bash
  NEXT_PUBLIC_API_URL=http://your-server:8000 docker compose up --build -d
  ```

### Registration Limits
Bonk is intended for private, self-hosted environments. You can control account registration using these variables in `backend/.env`:
- `ALLOW_REGISTRATION`: Set to `false` to disable registration entirely (default: `true`).
- `MAX_USERS`: Set a numerical limit on total registered accounts (default: `5`). Must be `>0`.

**Bootstrap Behaviour:** For a fresh installation with zero users, the first user registration is always allowed, regardless of the `ALLOW_REGISTRATION` and `MAX_USERS` settings. This ensures you can claim the initial admin/owner account safely.

### Production Safety Limits
Bonk includes built-in safeguards to protect against abuse when exposed to the Internet. These are configured in `backend/.env` with sensible defaults:
- `MAX_REQUEST_BODY_MB` (default `5`): Maximum size of an HTTP request body. Prevents memory exhaustion from large payloads.
- `RATE_LIMIT_LOGIN_MAX` / `RATE_LIMIT_LOGIN_WINDOW` (default `10` per `60`s): Brute-force protection for the login endpoint.
- `RATE_LIMIT_REGISTER_MAX` / `RATE_LIMIT_REGISTER_WINDOW` (default `5` per `60`s): Spam protection for account creation.
- `GIT_CLONE_TIMEOUT` (default `300`s): Maximum time allowed for `git clone` operations.
- `WEBHOOK_TIMEOUT` (default `10`s): Maximum time for application health checks (via HTTP requests) before failing deployment.
- `MAX_DEPLOYMENT_DURATION_MINUTES` (default `15`m): Limits how long a deployment pipeline can run.
- `MAX_CONCURRENT_DEPLOYMENTS` (default `2`): Number of simultaneous deployments processed by the ARQ worker.
- `MAX_DEPLOYMENT_LOG_MB` (default `10`): Truncates build logs to prevent disk exhaustion.
- `CONTAINER_CPU_LIMIT` (default `1.0`): Default CPU quota given to deployed application containers.
- `CONTAINER_MEMORY_LIMIT` (default `"512m"`): Default memory limit for deployed applications.
- `MAX_PROJECT_NAME_LENGTH` (default `64`), `MAX_REPO_URL_LENGTH` (default `256`): Validation limits for project attributes.
- `MAX_ENV_VARS_PER_PROJECT` (default `50`), `MAX_ENV_VAR_SIZE` (default `4096` bytes): Limits environment variable storage.

Additionally, the application adds robust security headers (e.g. `X-Frame-Options`, `X-Content-Type-Options`) on all endpoints.

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
