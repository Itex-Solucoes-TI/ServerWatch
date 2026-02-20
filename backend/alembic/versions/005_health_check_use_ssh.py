"""health_check_use_ssh

Revision ID: 005
Revises: 004
Create Date: 2026-02-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("health_checks", sa.Column("use_ssh", sa.Boolean(), server_default="false"))


def downgrade() -> None:
    op.drop_column("health_checks", "use_ssh")
