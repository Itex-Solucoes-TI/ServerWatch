from pydantic import BaseModel
from typing import Optional, List
from app.schemas.server import NetworkInterfaceCreate


class RouterCreate(BaseModel):
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    device_type: str = "ROUTER"
    has_vpn: bool = False
    has_external_ip: bool = False
    gateway: Optional[str] = None
    dns_primary: Optional[str] = None
    dns_secondary: Optional[str] = None
    wifi_ssid: Optional[str] = None
    wifi_band: Optional[str] = None
    wifi_channel: Optional[str] = None
    snmp_enabled: bool = False
    snmp_community: Optional[str] = None
    snmp_port: int = 161
    interfaces: Optional[List[NetworkInterfaceCreate]] = None
    create_ping_check: bool = False


class RouterUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    device_type: Optional[str] = None
    has_vpn: Optional[bool] = None
    has_external_ip: Optional[bool] = None
    gateway: Optional[str] = None
    dns_primary: Optional[str] = None
    dns_secondary: Optional[str] = None
    wifi_ssid: Optional[str] = None
    wifi_band: Optional[str] = None
    wifi_channel: Optional[str] = None
    snmp_enabled: Optional[bool] = None
    snmp_community: Optional[str] = None
    snmp_port: Optional[int] = None
    active: Optional[bool] = None


class RouterRead(BaseModel):
    id: int
    company_id: int
    name: str
    brand: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    device_type: str = "ROUTER"
    has_vpn: bool = False
    has_external_ip: bool = False
    gateway: Optional[str] = None
    dns_primary: Optional[str] = None
    dns_secondary: Optional[str] = None
    wifi_ssid: Optional[str] = None
    wifi_band: Optional[str] = None
    wifi_channel: Optional[str] = None
    snmp_enabled: bool = False
    snmp_community: Optional[str] = None
    snmp_port: int = 161
    active: bool = True
