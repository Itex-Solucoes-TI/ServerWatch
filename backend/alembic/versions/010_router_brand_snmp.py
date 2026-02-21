"""router_brand_snmp

Revision ID: 010
Revises: 009
"""
from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("routers", sa.Column("brand", sa.String(50), nullable=True))
    op.add_column("routers", sa.Column("snmp_enabled", sa.Boolean(), server_default="false"))
    op.add_column("routers", sa.Column("snmp_community", sa.String(64), nullable=True))
    op.add_column("routers", sa.Column("snmp_port", sa.Integer(), server_default="161"))


def downgrade() -> None:
    op.drop_column("routers", "snmp_port")
    op.drop_column("routers", "snmp_community")
    op.drop_column("routers", "snmp_enabled")
    op.drop_column("routers", "brand")
