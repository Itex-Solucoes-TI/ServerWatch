"""server_has_docker

Revision ID: 006
Revises: 005
Create Date: 2026-02-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("servers", sa.Column("has_docker", sa.Boolean(), server_default="false"))
    op.execute(
        "UPDATE servers SET has_docker = true WHERE docker_host IS NOT NULL OR ssh_host IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("servers", "has_docker")
