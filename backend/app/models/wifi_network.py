from sqlmodel import SQLModel, Field
from typing import Optional


class WifiNetwork(SQLModel, table=True):
    __tablename__ = "wifi_networks"
    id: Optional[int] = Field(default=None, primary_key=True)
    router_id: int = Field(foreign_key="routers.id")
    ssid: str
    band: Optional[str] = None      # 2.4GHz, 5GHz, 6GHz
    channel: Optional[str] = None
    password: Optional[str] = None
    vlan: Optional[str] = None
    notes: Optional[str] = None
    active: bool = Field(default=True)
