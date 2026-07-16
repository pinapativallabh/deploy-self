# Bonk

Bonk is a self-hosted application control plane that orchestrates deployment and operational management for applications running on developer-owned infrastructure.

---

## Architecture

```
                       ┌──────────────────────┐
                       │   Next.js Frontend   │
                       └──────────┬───────────┘
                                  │ HTTPS / WebSockets
                                  ▼
                       ┌──────────────────────┐
                       │   FastAPI Backend    │
                       └─────┬──────────┬─────┘
                             │          │
         Read/Write State    │          │ Push Job / Event
                             ▼          ▼
                      ┌──────────┐  ┌──────────┐
                      │PostgreSQL│  │  Redis   │
                      └──────────┘  └────┬─────┘
                                         │
                                         │ Pop Job
                                         ▼
                       ┌──────────────────────┐
                       │  Deployment Worker   │
                       └──────────┬───────────┘
                                  │ Docker SDK / socket
                                  ▼
                       ┌──────────────────────┐
                       │    Docker Engine     │
                       │ ───────────────────  │
                       │ [Managed Containers] │
                       └──────────────────────┘
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI |
| Frontend | Next.js, React, Tailwind CSS |
| Database | PostgreSQL 15 |
| Cache / Queue | Redis 7 |
| Migrations | Alembic + SQLAlchemy 2.x |
| Configuration | Pydantic Settings |
| Containers | Docker SDK |
| Orchestration | Docker Compose |

---

## Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- [Git](https://git-scm.com/)
- Python 3.11+ (for local development without Docker)

---

## Quick Start

### Using Docker Compose (recommended)

```bash
# Clone the repository
git clone https://github.com/pinapativallabh/deploy-self.git
cd deploy-self

# Start all services
docker compose up --build
```

This starts PostgreSQL, Redis, the backend, frontend, and worker. The backend waits for PostgreSQL and Redis health checks to pass before starting.

### Local Development (backend only)

```bash
# Start dependencies
docker compose up postgres redis -d

# Set up the backend
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env — set POSTGRES_HOST=localhost and REDIS_HOST=localhost

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Project Structure

```
bonk/
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── api/            # Route handlers and dependencies
│   │   │   ├── deps.py     # Dependency injection (DB sessions, Redis)
│   │   │   └── health.py   # GET /health endpoint
│   │   ├── core/           # Application infrastructure
│   │   │   ├── config.py   # Pydantic Settings (centralized configuration)
│   │   │   ├── logging.py  # Logging configuration
│   │   │   ├── redis.py    # Redis client lifecycle
│   │   │   └── exceptions.py  # Global exception handlers
│   │   ├── db/             # Database infrastructure
│   │   │   └── session.py  # SQLAlchemy engine, session factory, Base
│   │   ├── models/         # SQLAlchemy ORM models (future)
│   │   ├── schemas/        # Pydantic request/response schemas (future)
│   │   ├── services/       # Business logic layer (future)
│   │   └── utils/          # Shared utilities (future)
│   ├── alembic/            # Database migration scripts
│   │   ├── env.py          # Migration environment configuration
│   │   ├── script.py.mako  # Migration file template
│   │   └── versions/       # Migration files
│   ├── alembic.ini         # Alembic configuration
│   ├── .env                # Environment variables (not committed)
│   ├── .env.example        # Environment template
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # Next.js frontend
├── worker/                 # Deployment worker
├── docker-compose.yml
└── README.md
```

---

## Environment Variables

All configuration is managed through environment variables loaded by Pydantic Settings. The backend reads from `backend/.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `Bonk` | Application display name |
| `APP_ENV` | `development` | Environment: development, staging, production |
| `APP_VERSION` | `0.1.0` | Application version (reported in /health) |
| `LOG_LEVEL` | `info` | Log level: debug, info, warning, error |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |
| `POSTGRES_USER` | `bonk` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `bonk_dev_password` | PostgreSQL password |
| `POSTGRES_DB` | `bonk` | PostgreSQL database name |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host (`postgres` in Docker) |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `REDIS_HOST` | `localhost` | Redis host (`redis` in Docker) |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis database number |

---

## Migration Workflow

Bonk uses [Alembic](https://alembic.sqlalchemy.org/) for database migrations. All commands run from the `backend/` directory.

### Create a migration

```bash
# After modifying SQLAlchemy models:
alembic revision --autogenerate -m "describe the change"

# Review the generated file in alembic/versions/ before applying.
```

### Apply migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply inside Docker
docker compose exec backend alembic upgrade head
```

### Roll back migrations

```bash
# Roll back the last migration
alembic downgrade -1

# Roll back to a specific revision
alembic downgrade <revision_id>

# Roll back all migrations
alembic downgrade base
```

### View migration history

```bash
# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

---

## API Endpoints

### Health Check

```
GET /health
```

Reports application health including dependency status.

**200 OK** — all dependencies healthy:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "dependencies": {
    "postgres": { "status": "healthy" },
    "redis": { "status": "healthy" }
  }
}
```

**503 Service Unavailable** — one or more dependencies unreachable:
```json
{
  "status": "degraded",
  "version": "0.1.0",
  "environment": "development",
  "dependencies": {
    "postgres": { "status": "healthy" },
    "redis": { "status": "unhealthy", "error": "..." }
  }
}
```

---

## Development Philosophy

1. **Incremental Stability** — the codebase must compile, build, and pass checks after every commit.
2. **Explicit Code** — type-annotated, well-structured, no runtime tricks.
3. **Production Patterns** — database migrations, centralized error handling, structured logging.
4. **Clean Architecture** — decouple business logic from framework and infrastructure concerns.

---

## Current Status

**Phase 2 complete** — Backend foundation infrastructure.

### Completed
- ✅ Phase 1: Project skeleton, Docker Compose
- ✅ Phase 2: Configuration, database, Redis, Alembic, logging, error handling, health checks

### Roadmap
- Phase 3: Authentication
- Phase 4: Project management
- Phase 5: Deployment orchestration
- Phase 6: Docker SDK integration
- Phase 7: Background workers
- Phase 8: GitHub webhooks
- Phase 9: Deployment history
- Phase 10: Centralized logging
- Phase 11: Health monitoring
