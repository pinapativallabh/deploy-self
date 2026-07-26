"""Add the deployment-number uniqueness constraint declared by the ORM.

Revision ID: c4f0a0f8e91a
Revises: b743a34a19a6
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c4f0a0f8e91a"
down_revision: Union[str, None] = "b743a34a19a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_deployments_project_number",
        "deployments",
        ["project_id", "deployment_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_deployments_project_number", "deployments", type_="unique")
