# ForgeDeploy

ForgeDeploy is a self-hosted deployment platform (PaaS) inspired by Railway and Render, designed to automate containerized deployments from code repositories to local or remote Docker engines. It is designed to be a robust, production-quality tool for hosting personal projects, managing environments, and monitoring application health.

---

## 1. Project Vision & Problem Statement

### The Problem
Deploying personal projects or small client sites often forces developers into a trade-off:
- Use expensive public PaaS platforms (Railway, Render, Fly.io, Heroku) which have high markups on resources, limits on active free/cheap hobby tiers, and vendor lock-in.
- Set up complex Kubernetes clusters or low-level virtual machines (VPS) manually, which incurs significant DevOps overhead, scripting, and lack of a cohesive dashboard interface for monitoring and management.

### The Vision
ForgeDeploy bridges this gap by providing an easy-to-use, self-hosted platform. It runs on your own hardware or virtual private server (VPS). With ForgeDeploy, you get Git-triggered automatic deployments, env var management, real-time logging, and system health checks, all driven from a unified Next.js dashboard, without paying public PaaS markups.

---

## 2. Platform Goals
- **Production-Ready Quality**: Maintain strict robustness, security boundaries, and reliable state recovery.
- **GitOps Simplicity**: Enable automated Docker deployments triggered via GitHub Webhooks.
- **Unified Dashboard**: Monitor container health, view logs, and configure environment variables in one place.
- **Low Resource Overhead**: Run a lightweight control plane using FastAPI, Redis, and a dedicated worker, reserving hosting hardware capacity for customer applications.

---

## 3. High-Level Architecture

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

- **Frontend (Next.js + Tailwind CSS)**: Renders a modern, responsive web dashboard showing projects, services, deployments, environment settings, and container health.
- **Backend (FastAPI)**: Serves as the central API gateway. Handles user authentication (JWT), metadata storage, configuration storage, and webhook registration.
- **PostgreSQL**: Stores stateful relational data (users, projects, deployments, build configurations, logs metadata).
- **Redis Queue**: Acts as a reliable message broker/task queue to safely hand off deployment pipelines to workers.
- **Deployment Worker**: Python daemon that consumes deployment requests, checks out repository versions, runs Docker build pipelines, and deploys containers onto the host.
- **Docker Engine**: The underlying daemon executing the actual user application containers.

---

## 4. Technology Stack

- **Backend**: Python 3.11+, FastAPI (high-performance asynchronous framework)
- **Frontend**: Next.js (React), Tailwind CSS
- **Database**: PostgreSQL (relational database storage)
- **Task Queue**: Redis (message queue broker)
- **Authentication**: JWT (JSON Web Tokens) with cryptographically secure password hashing (bcrypt)
- **Container Management**: Docker SDK & Docker Compose
- **Version Control Integrations**: GitHub Webhooks & GitHub API

---

## 5. Repository Folder Structure

```
forge-deploy/
├── backend/            # FastAPI source code (models, routes, schemas)
├── frontend/           # Next.js frontend code (pages, components, styling)
├── worker/             # Deployment worker engine (deployment pipelines & Docker SDK integration)
├── docker/             # Configuration files for Docker/deployment environments
├── docs/               # System design documents and specifications
├── .gitignore          # Git ignore patterns
├── docker-compose.yml  # Local services coordinator (PostgreSQL, Redis)
└── README.md           # Project specification & documentation (this file)
```

---

## 6. Development Philosophy
1. **Incremental Stability**: The codebase must compile, build, and pass checks after every single commit.
2. **Explicit Code**: Avoid overly clever runtime tricks. Write explicit, type-annotated, and well-structured code.
3. **No Shortcuts in Production**: We implement production-grade patterns (e.g. database migrations, secure password handling, robust error recovery) rather than quick-and-dirty hacks.
4. **Clean Architecture**: Decouple business logic from external drivers (the framework, database layers, and the Docker daemon) to allow future extensibility.
