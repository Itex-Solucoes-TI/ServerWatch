"""installation_license

Revision ID: 008
Revises: 007
Create Date: 2026-02-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "installation_license",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("installation_license")
