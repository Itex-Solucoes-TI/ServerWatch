from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class DockerSnapshot(SQLModel, table=True):
    __tablename__ = "docker_snapshots"
    id: Optional[int] = Field(default=None, primary_key=True)
    server_id: int = Field(foreign_key="servers.id")
    container_id: str = Field(max_length=64)
    name: str
    image: str
    status: str
    cpu_percent: Optional[float] = None
    mem_percent: Optional[float] = None
    mem_usage_mb: Optional[float] = None
    synced_at: datetime = Field(default_factory=datetime.utcnow)
