from sqlmodel import SQLModel, Field
from typing import Optional


class NetworkLink(SQLModel, table=True):
    __tablename__ = "network_links"
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    name: Optional[str] = None
    source_server_id: Optional[int] = Field(default=None, foreign_key="servers.id")
    source_router_id: Optional[int] = Field(default=None, foreign_key="routers.id")
    target_server_id: Optional[int] = Field(default=None, foreign_key="servers.id")
    target_router_id: Optional[int] = Field(default=None, foreign_key="routers.id")
    link_type: str = Field(max_length=50)
    bandwidth_mbps: Optional[int] = None
    active: bool = Field(default=True)
