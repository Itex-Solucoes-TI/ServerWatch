from sqlmodel import SQLModel, Field
from sqlalchemy import Index
from datetime import datetime
from typing import Optional


class SnmpMetric(SQLModel, table=True):
    __tablename__ = "snmp_metrics"
    __table_args__ = (Index("ix_snmp_metrics_router_type_at", "router_id", "metric_type", "collected_at"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    router_id: int = Field(foreign_key="routers.id")
    metric_type: str  # TRAFFIC_IN, TRAFFIC_OUT, WIFI_CLIENTS, CPU, MEMORY, UPTIME
    interface_name: Optional[str] = None
    value: float
    unit: str  # bytes_sec, percent, count, seconds
    collected_at: datetime = Field(default_factory=datetime.utcnow)
