"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-02-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("cnpj", sa.String(20), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug")
    )
    op.create_table("users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email")
    )
    op.create_table("user_company_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="VIEWER"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("servers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("hostname", sa.String(), nullable=True),
        sa.Column("docker_host", sa.String(), nullable=True),
        sa.Column("environment", sa.String(), nullable=False, server_default="production"),
        sa.Column("os", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("routers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("has_vpn", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_external_ip", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("network_interfaces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=True),
        sa.Column("router_id", sa.Integer(), nullable=True),
        sa.Column("interface_name", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=False),
        sa.Column("subnet_mask", sa.String(), nullable=True),
        sa.Column("is_external", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_vpn", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("description", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["router_id"], ["routers.id"]),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("network_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("source_server_id", sa.Integer(), nullable=True),
        sa.Column("source_router_id", sa.Integer(), nullable=True),
        sa.Column("target_server_id", sa.Integer(), nullable=True),
        sa.Column("target_router_id", sa.Integer(), nullable=True),
        sa.Column("link_type", sa.String(50), nullable=False),
        sa.Column("bandwidth_mbps", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["source_router_id"], ["routers.id"]),
        sa.ForeignKeyConstraint(["source_server_id"], ["servers.id"]),
        sa.ForeignKeyConstraint(["target_router_id"], ["routers.id"]),
        sa.ForeignKeyConstraint(["target_server_id"], ["servers.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("node_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("node_type", sa.String(), nullable=False),
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False, server_default="0"),
        sa.Column("position_y", sa.Float(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "node_type", "node_id")
    )
    op.create_table("company_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("smtp_host", sa.String(), nullable=True),
        sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="587"),
        sa.Column("smtp_user", sa.String(), nullable=True),
        sa.Column("smtp_password", sa.String(), nullable=True),
        sa.Column("smtp_from", sa.String(), nullable=True),
        sa.Column("smtp_tls", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("zapi_instance_id", sa.String(), nullable=True),
        sa.Column("zapi_token", sa.String(), nullable=True),
        sa.Column("zapi_client_token", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id")
    )
    op.create_table("health_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=True),
        sa.Column("router_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("check_type", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("interval_sec", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("timeout_sec", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("expected_status", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["router_id"], ["routers.id"]),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("check_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("check_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["check_id"], ["health_checks.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_check_results_check_checked", "check_results", ["check_id", "checked_at"])
    op.create_table("docker_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("container_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("image", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("mem_percent", sa.Float(), nullable=True),
        sa.Column("mem_usage_mb", sa.Float(), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("notification_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("channel_type", sa.String(), nullable=False),
        sa.Column("target", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("alert_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("check_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("fail_threshold", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_notified_at", sa.DateTime(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["channel_id"], ["notification_channels.id"]),
        sa.ForeignKeyConstraint(["check_id"], ["health_checks.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_table("audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_audit_logs_company_created", "audit_logs", ["company_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("alert_rules")
    op.drop_table("notification_channels")
    op.drop_table("docker_snapshots")
    op.drop_index("ix_check_results_check_checked", "check_results")
    op.drop_table("check_results")
    op.drop_table("health_checks")
    op.drop_table("company_settings")
    op.drop_table("node_positions")
    op.drop_table("network_links")
    op.drop_table("network_interfaces")
    op.drop_table("routers")
    op.drop_table("servers")
    op.drop_table("user_company_roles")
    op.drop_table("users")
    op.drop_table("companies")
