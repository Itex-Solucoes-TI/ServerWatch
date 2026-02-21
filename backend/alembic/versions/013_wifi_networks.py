"""wifi_networks table

Revision ID: 013
Revises: 012
Create Date: 2026-02-21
"""
from alembic import op
import sqlalchemy as sa

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'wifi_networks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('router_id', sa.Integer(), sa.ForeignKey('routers.id'), nullable=False),
        sa.Column('ssid', sa.String(), nullable=False),
        sa.Column('band', sa.String(), nullable=True),
        sa.Column('channel', sa.String(), nullable=True),
        sa.Column('password', sa.String(), nullable=True),
        sa.Column('vlan', sa.String(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
    )


def downgrade():
    op.drop_table('wifi_networks')
