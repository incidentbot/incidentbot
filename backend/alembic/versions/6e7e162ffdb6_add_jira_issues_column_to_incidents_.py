"""Add jira_issues column to Incidents table

Revision ID: 6e7e162ffdb6
Revises: d1258401df8c
Create Date: 2023-02-09 17:16:41.946496

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict

# revision identifiers, used by Alembic.
revision = "6e7e162ffdb6"
down_revision = "d1258401df8c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "incidents", sa.Column("jira_issues", MutableDict.as_mutable(JSONB))
    )


def downgrade():
    pass
