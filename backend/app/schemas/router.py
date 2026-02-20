from pydantic import BaseModel
from typing import Optional


class RouterCreate(BaseModel):
    name: str
    model: Optional[str] = None
    location: Optional[str] = None
    has_vpn: bool = False
    has_external_ip: bool = False


class RouterUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    location: Optional[str] = None
    has_vpn: Optional[bool] = None
    has_external_ip: Optional[bool] = None
    active: Optional[bool] = None


class RouterRead(RouterCreate):
    id: int
    company_id: int
    active: bool
