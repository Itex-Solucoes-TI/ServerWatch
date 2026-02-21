"""camera rtsp fields on generic_devices

Revision ID: 016
Revises: 015
Create Date: 2026-02-21
"""
from alembic import op
import sqlalchemy as sa

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('generic_devices', sa.Column('rtsp_username', sa.String(), nullable=True))
    op.add_column('generic_devices', sa.Column('rtsp_password', sa.String(), nullable=True))
    op.add_column('generic_devices', sa.Column('rtsp_port', sa.Integer(), nullable=False, server_default='554'))
    op.add_column('generic_devices', sa.Column('rtsp_path', sa.String(), nullable=True))


def downgrade():
    op.drop_column('generic_devices', 'rtsp_username')
    op.drop_column('generic_devices', 'rtsp_password')
    op.drop_column('generic_devices', 'rtsp_port')
    op.drop_column('generic_devices', 'rtsp_path')
