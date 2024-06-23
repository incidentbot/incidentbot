"""Rename conference_bridge col to meeting_link

Revision ID: 460305cbabee
Revises: 0018a13f433d
Create Date: 2024-06-22 20:13:57.453351

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "460305cbabee"
down_revision = "0018a13f433d"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "incidents", "conference_bridge", new_column_name="meeting_link"
    )


def downgrade():
    pass
