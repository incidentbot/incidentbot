"""Add column to track pagerduty incidents

Revision ID: 20b507f90f5e
Revises: 1be0468c576c
Create Date: 2022-12-17 22:55:03.125857

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20b507f90f5e"
down_revision = "1be0468c576c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("incidents", sa.Column("pagerduty_incidents", sa.JSON()))


def downgrade():
    pass
