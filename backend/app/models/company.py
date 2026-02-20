from sqlmodel import SQLModel, Field
from datetime import datetime, date
from typing import Optional


class Company(SQLModel, table=True):
    __tablename__ = "companies"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    slug: str = Field(max_length=100, unique=True)
    cnpj: Optional[str] = Field(default=None, max_length=20)
    license_valid_until: Optional[date] = Field(default=None)
    license_cnpj: Optional[str] = Field(default=None, max_length=20)
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
