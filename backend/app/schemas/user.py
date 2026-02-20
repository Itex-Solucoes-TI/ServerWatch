from pydantic import BaseModel
from typing import Optional


class CompanyRoleItem(BaseModel):
    company_id: int
    role: str


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "VIEWER"
    company_roles: Optional[list[CompanyRoleItem]] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    company_roles: Optional[list[CompanyRoleItem]] = None


class UserRead(BaseModel):
    id: int
    name: str
    email: str
    role: Optional[str] = None
    is_superadmin: bool = False
