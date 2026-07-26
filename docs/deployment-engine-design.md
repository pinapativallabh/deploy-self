# Deployment engine design

## Purpose

A deployment is an immutable attempt to deploy one revision of a project. Project configuration can change over time; each deployment records the branch, resolved commit SHA, state, timestamps, logs, and failure reason for that attempt.

## Lifecycle

```text
PENDING -> CLONING -> BUILDING -> STARTING -> RUNNING
                         |            |
                         +--> FAILED <-+
```

Pending, cloning, and building deployments can be marked `CANCELED` when superseded. `RUNNING`, `FAILED`, `CANCELED`, and `ARCHIVED` are terminal states.

## Execution flow

1. The API creates a `PENDING` deployment and enqueues its ID in ARQ.
2. The worker resolves the repository revision into the persistent repository cache.
3. The worker builds an image from the project build context and Dockerfile.
4. The worker starts a uniquely named container with the project's environment variables.
5. The worker waits for the configured health endpoint to return HTTP 200.
6. On success, the worker marks the deployment `RUNNING`, promotes it as the project's active deployment, and removes the prior active container.
7. On failure, the worker preserves the previous active deployment, records the failure, and removes the failed container.

## Retention and rollback

Deployment records are retained as project history. Containers and images are cleaned up after the configured successful-deployment retention limit. A rollback creates a new deployment pinned to a previously successful deployment's commit SHA, preserving a complete audit trail.

## Operational constraints

The worker uses the host Docker daemon through a mounted socket. This is a privileged boundary: only trusted operators and repositories should be allowed to use an installation. Cleanup intentionally avoids Docker network pruning because the daemon can host unrelated workloads.
