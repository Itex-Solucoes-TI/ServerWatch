from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class NotificationChannel(SQLModel, table=True):
    __tablename__ = "notification_channels"
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    name: str = Field(max_length=100)
    channel_type: str
    target: str
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AlertRule(SQLModel, table=True):
    __tablename__ = "alert_rules"
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    check_id: int = Field(foreign_key="health_checks.id")
    channel_id: int = Field(foreign_key="notification_channels.id")
    fail_threshold: int = Field(default=3)
    active: bool = Field(default=True)
    last_notified_at: Optional[datetime] = None
    consecutive_failures: int = Field(default=0)
