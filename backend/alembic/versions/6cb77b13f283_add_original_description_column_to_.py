"""Add original description column to Incidents table

Revision ID: 6cb77b13f283
Revises: ca70b39d39ed
Create Date: 2022-12-09 17:45:35.297697

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6cb77b13f283"
down_revision = "ca70b39d39ed"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("incidents", sa.Column("channel_description", sa.String()))


def downgrade():
    pass
