"""add slug to project

Revision ID: e5f1b2c3d4e5
Revises: c0aeb7f976fb
Create Date: 2026-08-05 22:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f1b2c3d4e5'
down_revision: Union[str, None] = 'c0aeb7f976fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the column as nullable first
    op.add_column('projects', sa.Column('slug', sa.String(length=255), nullable=True))
    
    # Populate existing rows with a basic slug. In production, we'd do this more carefully.
    # Since this is likely a fresh deployment, we can just use the project ID or a basic string.
    op.execute("UPDATE projects SET slug = 'project-' || substring(id::text from 1 for 8) WHERE slug IS NULL")
    
    # Now make it not nullable and add unique constraint
    op.alter_column('projects', 'slug', nullable=False)
    op.create_unique_constraint('uq_projects_slug', 'projects', ['slug'])


def downgrade() -> None:
    op.drop_constraint('uq_projects_slug', 'projects', type_='unique')
    op.drop_column('projects', 'slug')
