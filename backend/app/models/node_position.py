from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint
from typing import Optional


class NodePosition(SQLModel, table=True):
    __tablename__ = "node_positions"
    __table_args__ = (UniqueConstraint("company_id", "node_type", "node_id"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="companies.id")
    node_type: str
    node_id: int
    position_x: float = Field(default=0)
    position_y: float = Field(default=0)
