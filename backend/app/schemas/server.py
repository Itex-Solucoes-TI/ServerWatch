from pydantic import BaseModel
from typing import Optional, List


class NetworkInterfaceCreate(BaseModel):
    interface_name: Optional[str] = None
    ip_address: str
    subnet_mask: Optional[str] = None
    is_external: bool = False
    is_vpn: bool = False
    is_primary: bool = False


class NetworkInterfaceRead(NetworkInterfaceCreate):
    id: int
    server_id: Optional[int]
    router_id: Optional[int]


class ServerCreate(BaseModel):
    name: str
    hostname: Optional[str] = None
    has_docker: bool = False
    docker_host: Optional[str] = None
    docker_tls_ca_cert: Optional[str] = None
    docker_tls_client_cert: Optional[str] = None
    docker_tls_client_key: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    environment: str = "production"
    os: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    has_docker: Optional[bool] = None
    docker_host: Optional[str] = None
    docker_tls_ca_cert: Optional[str] = None
    docker_tls_client_cert: Optional[str] = None
    docker_tls_client_key: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    ssh_password: Optional[str] = None
    environment: Optional[str] = None
    os: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None


class ServerRead(ServerCreate):
    id: int
    company_id: int
    active: bool
