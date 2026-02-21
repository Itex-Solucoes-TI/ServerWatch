"""network_link add generic_device columns

Revision ID: 015
Revises: 014
Create Date: 2026-02-21
"""
from alembic import op
import sqlalchemy as sa

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('network_links', sa.Column('source_generic_id', sa.Integer(), sa.ForeignKey('generic_devices.id'), nullable=True))
    op.add_column('network_links', sa.Column('target_generic_id', sa.Integer(), sa.ForeignKey('generic_devices.id'), nullable=True))


def downgrade():
    op.drop_column('network_links', 'source_generic_id')
    op.drop_column('network_links', 'target_generic_id')
