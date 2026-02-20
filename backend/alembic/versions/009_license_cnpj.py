"""license_cnpj

Revision ID: 009
Revises: 008
Create Date: 2026-02-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("installation_license", sa.Column("cnpj", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("installation_license", "cnpj")
