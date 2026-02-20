from datetime import date
from typing import Optional
from sqlmodel import SQLModel, Field


class InstallationLicense(SQLModel, table=True):
    __tablename__ = "installation_license"
    id: Optional[int] = Field(default=None, primary_key=True)
    cnpj: Optional[str] = Field(default=None, max_length=20)
    valid_until: date = Field()
