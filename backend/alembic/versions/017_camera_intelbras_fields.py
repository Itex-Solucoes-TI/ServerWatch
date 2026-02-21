"""camera intelbras fields (channel, subtype) replace rtsp_path

Revision ID: 017
Revises: 016
Create Date: 2026-02-21
"""
from alembic import op
import sqlalchemy as sa

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('generic_devices', 'rtsp_path')
    op.add_column('generic_devices', sa.Column('rtsp_channel', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('generic_devices', sa.Column('rtsp_subtype', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.add_column('generic_devices', sa.Column('rtsp_path', sa.String(), nullable=True))
    op.drop_column('generic_devices', 'rtsp_channel')
    op.drop_column('generic_devices', 'rtsp_subtype')
