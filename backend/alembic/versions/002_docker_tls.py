"""docker_tls

Revision ID: 002
Revises: 001
Create Date: 2026-02-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("servers", sa.Column("docker_tls_ca_cert", sa.Text(), nullable=True))
    op.add_column("servers", sa.Column("docker_tls_client_cert", sa.Text(), nullable=True))
    op.add_column("servers", sa.Column("docker_tls_client_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("servers", "docker_tls_client_key")
    op.drop_column("servers", "docker_tls_client_cert")
    op.drop_column("servers", "docker_tls_ca_cert")
