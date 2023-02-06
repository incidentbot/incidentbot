"""Add sp_incident_data column to Incidents table

Revision ID: d1258401df8c
Revises: 0a8a3a1f6f6e
Create Date: 2023-02-04 20:24:45.271119

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d1258401df8c"
down_revision = "0a8a3a1f6f6e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("incidents", sa.Column("sp_incident_data", sa.JSON()))


def downgrade():
    pass
