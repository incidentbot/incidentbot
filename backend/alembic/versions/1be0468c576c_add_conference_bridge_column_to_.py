"""Add conference bridge column to Incidents table

Revision ID: 1be0468c576c
Revises: 6cb77b13f283
Create Date: 2022-12-16 11:42:41.345215

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1be0468c576c"
down_revision = "6cb77b13f283"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("incidents", sa.Column("conference_bridge", sa.String()))


def downgrade():
    pass
