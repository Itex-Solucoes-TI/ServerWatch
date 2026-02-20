from sqlmodel import SQLModel, Field
from typing import Optional


class NetworkInterface(SQLModel, table=True):
    __tablename__ = "network_interfaces"
    id: Optional[int] = Field(default=None, primary_key=True)
    server_id: Optional[int] = Field(default=None, foreign_key="servers.id")
    router_id: Optional[int] = Field(default=None, foreign_key="routers.id")
    interface_name: Optional[str] = None
    ip_address: str
    subnet_mask: Optional[str] = None
    is_external: bool = Field(default=False)
    is_vpn: bool = Field(default=False)
    is_primary: bool = Field(default=False)
    description: Optional[str] = None
