"""docker_ssh

Revision ID: 003
Revises: 002
Create Date: 2026-02-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("servers", sa.Column("docker_ssh_host", sa.String(), nullable=True))
    op.add_column("servers", sa.Column("docker_ssh_port", sa.Integer(), nullable=True))
    op.add_column("servers", sa.Column("docker_ssh_user", sa.String(), nullable=True))
    op.add_column("servers", sa.Column("docker_ssh_password", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("servers", "docker_ssh_password")
    op.drop_column("servers", "docker_ssh_user")
    op.drop_column("servers", "docker_ssh_port")
    op.drop_column("servers", "docker_ssh_host")
