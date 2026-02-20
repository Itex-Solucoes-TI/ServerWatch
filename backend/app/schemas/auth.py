from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class SwitchRequest(BaseModel):
    company_id: int


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict
    companies: list
