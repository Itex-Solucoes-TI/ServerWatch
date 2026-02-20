from sqlmodel import SQLModel, Field
from sqlalchemy import Index
from datetime import datetime
from typing import Optional


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_company_created", "company_id", "created_at"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: Optional[int] = Field(default=None, foreign_key="companies.id")
    user_id: int = Field(foreign_key="users.id")
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
