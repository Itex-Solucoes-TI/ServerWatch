"""router device type and network fields

Revision ID: 012
Revises: 011
Create Date: 2026-02-21
"""
from alembic import op
import sqlalchemy as sa

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('routers', sa.Column('device_type', sa.String(), nullable=False, server_default='ROUTER'))
    op.add_column('routers', sa.Column('gateway', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('dns_primary', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('dns_secondary', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('wifi_ssid', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('wifi_band', sa.String(), nullable=True))
    op.add_column('routers', sa.Column('wifi_channel', sa.String(), nullable=True))


def downgrade():
    for col in ['device_type', 'gateway', 'dns_primary', 'dns_secondary', 'wifi_ssid', 'wifi_band', 'wifi_channel']:
        op.drop_column('routers', col)
