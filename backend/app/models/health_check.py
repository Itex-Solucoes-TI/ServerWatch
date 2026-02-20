from sqlmodel import SQLModel, Field
from sqlalchemy import Index
from datetime import datetime
from typing import Optional


class HealthCheck(SQLModel, table=True):
    __tablename__ = "health_checks"
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    server_id: Optional[int] = Field(default=None, foreign_key="servers.id")
    router_id: Optional[int] = Field(default=None, foreign_key="routers.id")
    name: str
    check_type: str
    target: str
    interval_sec: int = Field(default=60)
    timeout_sec: int = Field(default=10)
    expected_status: Optional[int] = None
    use_ssh: bool = Field(default=False)
    active: bool = Field(default=True)
    last_checked_at: Optional[datetime] = None


class CheckResult(SQLModel, table=True):
    __tablename__ = "check_results"
    __table_args__ = (Index("ix_check_results_check_checked", "check_id", "checked_at"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    check_id: int = Field(foreign_key="health_checks.id")
    status: str
    latency_ms: Optional[int] = None
    message: Optional[str] = None
    checked_at: datetime = Field(default_factory=datetime.utcnow)
