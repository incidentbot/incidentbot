"""Change user password field to no limit

Revision ID: 0018a13f433d
Revises: 00417e13021a
Create Date: 2024-03-08 19:16:38.209490

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0018a13f433d"
down_revision = "00417e13021a"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("users", "password")
    op.add_column("users", sa.Column("password", sa.String()))


def downgrade():
    pass
