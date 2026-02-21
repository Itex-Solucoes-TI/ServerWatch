from sqlmodel import SQLModel, Field
from typing import Optional


class GenericDevice(SQLModel, table=True):
    """Dispositivos genéricos na topologia (câmeras, impressoras, etc.)."""
    __tablename__ = "generic_devices"
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    name: str = Field(max_length=100)
    # CAMERA, PRINTER, OTHER
    device_type: str = Field(default="OTHER")
    ip_address: Optional[str] = None
    notes: Optional[str] = None
    active: bool = Field(default=True)
    # Campos específicos para câmeras IP (padrão Intelbras)
    rtsp_username: Optional[str] = None
    rtsp_password: Optional[str] = None
    rtsp_port: int = Field(default=554)
    rtsp_channel: int = Field(default=1)    # número do canal da câmera
    rtsp_subtype: int = Field(default=0)    # 0=principal, 1=extra
