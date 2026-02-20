from sqlmodel import SQLModel, Field
from typing import Optional


class Router(SQLModel, table=True):
    __tablename__ = "routers"
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    name: str = Field(max_length=100)
    model: Optional[str] = None
    location: Optional[str] = None
    has_vpn: bool = Field(default=False)
    has_external_ip: bool = Field(default=False)
    active: bool = Field(default=True)
