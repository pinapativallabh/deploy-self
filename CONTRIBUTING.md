# Contributing to Bonk

Thank you for contributing. Bonk manages deployments and has access to a Docker daemon, so correctness and security take priority over feature velocity.

## Before you start

1. Open an issue to discuss substantial changes before implementing them.
2. Keep pull requests focused and avoid unrelated formatting or dependency updates.
3. Never commit secrets, local `.env` files, generated build output, deployment logs, or Docker credentials.

## Local setup

```bash
cp .env.example backend/.env
docker compose up --build -d
```

The service status and API health can be checked with:

```bash
docker compose ps
curl http://localhost:8000/health
```

## Quality checks

Run these checks before opening a pull request:

```bash
cd frontend
npm ci
npm run lint
npm run build

cd ..
docker compose build
docker compose exec backend alembic current
```

When changing database models, create and review an Alembic migration. Do not edit an already-applied migration.

## Pull requests

Describe the problem, the approach, validation performed, and any operational impact. Update user-facing or operational documentation when behavior, configuration, APIs, or deployment procedures change.
