"""generic_devices table

Revision ID: 014
Revises: 013
Create Date: 2026-02-21
"""
from alembic import op
import sqlalchemy as sa

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'generic_devices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_id', sa.Integer(), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('device_type', sa.String(), nullable=False, server_default='OTHER'),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
    )


def downgrade():
    op.drop_table('generic_devices')
