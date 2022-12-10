"""Add security column to Incidents table

Revision ID: ca70b39d39ed
Revises: 
Create Date: 2022-12-09 15:56:17.464247

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ca70b39d39ed"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("incidents", sa.Column("is_security_incident", sa.BOOLEAN()))


def downgrade():
    op.drop_column("incidents", "is_security_incident")
