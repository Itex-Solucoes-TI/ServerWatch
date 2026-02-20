from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class Server(SQLModel, table=True):
    __tablename__ = "servers"
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    name: str = Field(max_length=100)
    hostname: Optional[str] = None
    has_docker: bool = Field(default=False)
    docker_host: Optional[str] = None
    docker_tls_ca_cert: Optional[str] = None
    docker_tls_client_cert: Optional[str] = None
    docker_tls_client_key: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    environment: str = Field(default="production")
    os: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
