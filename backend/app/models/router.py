from sqlmodel import SQLModel, Field
from typing import Optional


class Router(SQLModel, table=True):
    __tablename__ = "routers"
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    name: str = Field(max_length=100)
    brand: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    # Tipo: ROUTER, WIFI_AP, SWITCH, FIREWALL, OTHER
    device_type: str = Field(default="ROUTER")
    has_vpn: bool = Field(default=False)
    has_external_ip: bool = Field(default=False)
    # Rede
    gateway: Optional[str] = None
    dns_primary: Optional[str] = None
    dns_secondary: Optional[str] = None
    # WiFi (preenchido quando device_type = WIFI_AP)
    wifi_ssid: Optional[str] = None
    wifi_band: Optional[str] = None   # 2.4GHz, 5GHz, 6GHz, Dual, Tri
    wifi_channel: Optional[str] = None
    snmp_enabled: bool = Field(default=False)
    snmp_community: Optional[str] = None
    snmp_port: int = Field(default=161)
    active: bool = Field(default=True)
