"""add archived to deploymentstatus

Revision ID: c0aeb7f976fb
Revises: 24d2467bceb0
Create Date: 2026-07-27 10:41:20.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0aeb7f976fb'
down_revision = '24d2467bceb0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE deploymentstatus ADD VALUE IF NOT EXISTS 'ARCHIVED'")


def downgrade() -> None:
    pass
