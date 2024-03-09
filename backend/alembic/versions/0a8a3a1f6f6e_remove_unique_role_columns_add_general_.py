"""Remove unique role columns, add general role column

Revision ID: 0a8a3a1f6f6e
Revises: 20b507f90f5e
Create Date: 2023-01-14 21:36:33.702620

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict

# revision identifiers, used by Alembic.
revision = "0a8a3a1f6f6e"
down_revision = "20b507f90f5e"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("incidents", "commander")
    op.drop_column("incidents", "technical_lead")
    op.drop_column("incidents", "communications_liaison")
    op.add_column(
        "incidents", sa.Column("roles", MutableDict.as_mutable(JSONB))
    )


def downgrade():
    pass
