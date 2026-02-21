from sqlmodel import SQLModel, Field
from typing import Optional


class SnmpMonitor(SQLModel, table=True):
    """Define o que monitorar via SNMP em um roteador."""
    __tablename__ = "snmp_monitors"
    id: Optional[int] = Field(default=None, primary_key=True)
    router_id: int = Field(foreign_key="routers.id")
    metric_type: str  # TRAFFIC, WIFI_CLIENTS, CPU, MEMORY
    custom_oid: Optional[str] = None  # OID customizado; None = usar padrão
    interface_filter: Optional[str] = None  # Filtro de interface para tráfego (ex: "eth0", "wlan0")
    interval_sec: int = Field(default=60)
    threshold_warn: Optional[float] = None  # Alerta quando valor >= threshold
    threshold_unit: Optional[str] = None  # percentual, bytes_sec, count
    active: bool = Field(default=True)
