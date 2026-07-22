# Phase 5 — Deployment Engine Design

This document outlines the architectural design for the Bonk Deployment Engine. It is designed to be simple enough for an MVP while remaining robust, extensible, and capable of supporting future enterprise features like zero-downtime deployments and rollbacks.

---

## 1. What exactly is a Deployment?

**Definition:** "A Deployment is one immutable attempt to deploy one immutable revision of a Project."

**Why it exists separately from Project:**
* **Immutability:** Only status, timestamps and error information may change after creation. A Project is a mutable configuration (e.g., "Frontend App", repo URL, env vars).
* **Separation of Concerns:** Projects define *what* to deploy; Deployments track *how* and *when* it was executed.
* **Audit & Rollback:** To rollback, we don't modify the Project configuration; we simply start a previous, known-good Deployment.

---

## 2. Relationship: Project ↔ Deployment

**1 Project → Many Deployments**

**Reasoning:**
* **Traceability:** Every time code is pushed or a manual trigger occurs, a new Deployment is created. We need a strict 1-to-N relationship to maintain a ledger of builds.
* **State Management:** A single project can have multiple deployments in various lifecycle states (e.g., `v3` is `RUNNING` and serving traffic, while `v4` is currently `BUILDING`).
* **Active Deployment:** The Project should reference the currently active deployment. This simplifies lookups and routing, as finding the production container is a direct foreign key on the Project, rather than requiring a complex subquery filtering by status and date.

---

## 3. Lifecycle & State Machine

The deployment state machine should be linear and explicit.

**The Pipeline:**
`PENDING` ➔ `CLONING` ➔ `BUILDING` ➔ `STARTING` ➔ `RUNNING` (Terminal Success)

*(Any state can transition to `FAILED` or `CANCELED`)*

**State Definitions:**
* `PENDING`: Request acknowledged, waiting for a worker to pick it up.
* `CLONING`: Fetching source code via Git.
* `BUILDING`: Executing the Docker build process.
* `STARTING`: Running the container and waiting for the application to boot.
* `RUNNING`: The deployment was successful. Health monitoring will belong to the Runtime phase.
* `FAILED`: An error occurred (e.g., compilation error, git auth failure).
* `CANCELED`: Superseded by a newer deployment or manually aborted by the user.

---

## 4. Deployment History

**Should Bonk keep previous deployments?** Yes.

**Reasoning & Strategy:**
* **Database Records:** Deployment metadata (logs, commit SHAs, durations) should be kept indefinitely. They are lightweight and crucial for observability.
* **Infrastructure Pruning:** Docker Images and Containers consume significant disk space. Bonk should implement a pruning strategy (e.g., retaining only the last 3-5 `RUNNING` images per project).
* **Cleanup:** Old deployment records are only deleted via cascade when the parent Project is deleted.

---

## 5. Failure Recovery

**If a deployment fails, what happens?**
* **Rule:** The previously active `RUNNING` deployment **must remain untouched and running**.
* **Zero-Downtime Principle:** Traffic is only cut over to the new container *after* it reaches the `RUNNING` state. 
* **Tradeoffs:** This requires briefly running two instances of the application concurrently (consuming more RAM/CPU on the host server). However, the UX tradeoff is mandatory: a failed build should never take a production application offline. 

---

## 6. Concurrency Handling

**Scenario: User presses "Deploy" 5 times rapidly.**

**Behavior: Cancel & Replace**
* If a new deployment is triggered while an older one is in `PENDING`, `CLONING`, or `BUILDING`, the older deployment should be aggressively moved to `CANCELED`.
* **Why?** The user only cares about the latest state of their code. Expending CPU and network bandwidth building an obsolete commit is a waste of server resources.
* If an existing deployment is already `STARTING` (about to become running), the new deployment should simply remain `PENDING` until the lock is released.

---

## 7. Database Design (Deployment Entity)

The table design focuses on orchestration and auditing, rejecting unnecessary heavy data.

* `id` (UUID, PK): Primary identifier.
* `project_id` (UUID, FK): Association to the parent Project.
* `deployment_number` (Integer): A sequential deployment number for each project. UUID remains primary key, this is for user-facing history (e.g., "Deployment #4").
* `status` (String/Enum): Current state (e.g., `BUILDING`, `RUNNING`).
* `branch` (String): The Git branch being deployed.
* `commit_sha` (String, nullable): The exact git hash being built.
* `commit_message` (String, nullable): Displayed in the UI for context.
* `logs_path` (String, nullable): Filepath or identifier where raw build logs are stored.
* `error_message` (Text, nullable): Short human-readable reason if `FAILED`.
* `started_at` (DateTime, nullable): Timestamp when worker picked it up.
* `finished_at` (DateTime, nullable): Timestamp of terminal state. Deployment duration is derived from `finished_at - started_at` (do not store duration separately).

---

## 8. Relationship to Docker (Loose Coupling)

* **Deployment (Domain Model)** knows: "I am deployment ID `123`, I am for `project X`, and my status is `BUILDING`."
* **DockerService (Infrastructure)** knows: "Given a directory and an image tag, I will execute a build and return a container ID."
* **The Orchestrator:** The `DeploymentService` acts as the orchestrator. It orchestrates:
    * `GitService`
    * `DockerService`
    * `Database`
  `GitService` and `DockerService` must not depend on each other. The Database records should NOT permanently store Docker container IDs or image IDs unless a future requirement justifies it.

---

## 9. Future-Proofing

This simple schema sets a solid foundation for future features without requiring implementation now:
* **Rollbacks:** Triggering a rollback is as simple as creating a new Deployment record passing in an older `commit_sha`.
* **Deployment Logs:** Logs can be streamed to a local file system via Docker SDK, and `logs_path` in the DB points to that file for the API to read later.
* **Metrics:** A simple SQL query on `finished_at - started_at` gives deployment duration trends.

---

## 10. Architecture Flow

**The execution pipeline follows a clear Layered Architecture:**

1. **User / API:** POST `/projects/{id}/deploy`
2. **Router:** Validates ownership, calls `DeploymentService`.
3. **DeploymentService (Synchronous):** Creates a `PENDING` Deployment in PostgreSQL. Dispatches an async background task to the worker. Returns `202 Accepted` with the deployment ID.
4. **Worker (Asynchronous Engine):**
   * Updates DB ➔ `CLONING`
   * Calls `GitService`
   * Updates DB ➔ `BUILDING`
   * Calls `DockerService` (Build)
   * Updates DB ➔ `STARTING`
   * Calls `DockerService` (Run Container)
   * Updates DB ➔ `RUNNING` (and tears down the old container). Project `active_deployment_id` is updated.
5. **State Retrieval:** The frontend polls `GET /deployments/{id}` to reflect the changing `status` to the user in real-time.
