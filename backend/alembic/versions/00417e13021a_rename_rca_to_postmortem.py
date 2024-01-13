"""Rename rca to postmortem

Revision ID: 00417e13021a
Revises: 6e7e162ffdb6
Create Date: 2024-01-13 16:06:10.387681

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "00417e13021a"
down_revision = "6e7e162ffdb6"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("incidents", "rca", new_column_name="postmortem")


def downgrade():
    pass
