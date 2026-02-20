from pydantic import BaseModel
from typing import Optional


class CompanyCreate(BaseModel):
    name: str
    slug: str
    cnpj: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    cnpj: Optional[str] = None
    active: Optional[bool] = None


class CompanyRead(BaseModel):
    id: int
    name: str
    slug: str
    cnpj: Optional[str]
    active: bool
