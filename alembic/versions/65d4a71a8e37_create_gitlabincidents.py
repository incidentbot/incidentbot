"""create gitlabincidents

Revision ID: 65d4a71a8e37
Revises: d3da32cf941c
Create Date: 2025-10-15 09:30:32.388389

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '65d4a71a8e37'
down_revision = 'd3da32cf941c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "gitlabissuerecord",
        sa.Column("id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("iid", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("parent", sa.Integer(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent"],
            ["incidentrecord.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("gitlabissuerecord")
