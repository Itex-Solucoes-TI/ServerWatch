from sqlmodel import SQLModel, Field
from typing import Optional


class CompanySettings(SQLModel, table=True):
    __tablename__ = "company_settings"
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id", unique=True)
    smtp_host: Optional[str] = None
    smtp_port: int = Field(default=587)
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_tls: bool = Field(default=True)
    zapi_instance_id: Optional[str] = None
    zapi_token: Optional[str] = None
    zapi_client_token: Optional[str] = None
