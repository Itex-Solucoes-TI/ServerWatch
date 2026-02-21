"""snmp_metrics_and_monitors

Revision ID: 011
Revises: 010
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "snmp_monitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("router_id", sa.Integer(), sa.ForeignKey("routers.id"), nullable=False),
        sa.Column("metric_type", sa.String(32), nullable=False),
        sa.Column("custom_oid", sa.String(255), nullable=True),
        sa.Column("interface_filter", sa.String(64), nullable=True),
        sa.Column("interval_sec", sa.Integer(), server_default="60"),
        sa.Column("threshold_warn", sa.Float(), nullable=True),
        sa.Column("threshold_unit", sa.String(32), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true"),
    )
    op.create_table(
        "snmp_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("router_id", sa.Integer(), sa.ForeignKey("routers.id"), nullable=False),
        sa.Column("metric_type", sa.String(32), nullable=False),
        sa.Column("interface_name", sa.String(64), nullable=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("collected_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_snmp_metrics_router_type_at", "snmp_metrics", ["router_id", "metric_type", "collected_at"])


def downgrade() -> None:
    op.drop_index("ix_snmp_metrics_router_type_at", "snmp_metrics")
    op.drop_table("snmp_metrics")
    op.drop_table("snmp_monitors")
