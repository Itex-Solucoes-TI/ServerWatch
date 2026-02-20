"""ssh_generic

Revision ID: 004
Revises: 003
Create Date: 2026-02-18

"""
from typing import Sequence, Union
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE servers RENAME COLUMN docker_ssh_host TO ssh_host")
    op.execute("ALTER TABLE servers RENAME COLUMN docker_ssh_port TO ssh_port")
    op.execute("ALTER TABLE servers RENAME COLUMN docker_ssh_user TO ssh_user")
    op.execute("ALTER TABLE servers RENAME COLUMN docker_ssh_password TO ssh_password")


def downgrade() -> None:
    op.execute("ALTER TABLE servers RENAME COLUMN ssh_host TO docker_ssh_host")
    op.execute("ALTER TABLE servers RENAME COLUMN ssh_port TO docker_ssh_port")
    op.execute("ALTER TABLE servers RENAME COLUMN ssh_user TO docker_ssh_user")
    op.execute("ALTER TABLE servers RENAME COLUMN ssh_password TO docker_ssh_password")
