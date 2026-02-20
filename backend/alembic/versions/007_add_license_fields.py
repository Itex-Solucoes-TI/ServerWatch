"""add_license_fields

Revision ID: 007
Revises: 006
Create Date: 2026-02-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("license_valid_until", sa.Date(), nullable=True))
    op.add_column("companies", sa.Column("license_cnpj", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "license_cnpj")
    op.drop_column("companies", "license_valid_until")
