"""create phareincidents

Revision ID: 3f8c2a1b9d04
Revises: 65d4a71a8e37
Create Date: 2026-03-09 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "3f8c2a1b9d04"
down_revision = "65d4a71a8e37"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "phareincidentrecord",
        sa.Column("channel_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_ts", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("parent", sa.Integer(), nullable=False),
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("updates", sa.JSON(), nullable=True),
        sa.Column("upstream_id", sa.Integer(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent"],
            ["incidentrecord.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("phareincidentrecord")
