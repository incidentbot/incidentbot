"""Add resolved_at to incidentrecord

Revision ID: f1a2b3c4d5e6
Revises: eeebefcd37d6
Create Date: 2026-06-09 14:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "eeebefcd37d6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "incidentrecord",
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("incidentrecord", "resolved_at")
