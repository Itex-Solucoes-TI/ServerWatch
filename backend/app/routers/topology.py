from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.deps import get_session, get_company_id, require_role
from app.models.network_link import NetworkLink
from app.models.node_position import NodePosition
from app.services.topology_service import get_graph

router = APIRouter(prefix="/topology", tags=["topology"])


@router.get("")
def get_topology(
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    return get_graph(session, company_id)


@router.post("/links")
def create_link(
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    link = NetworkLink(company_id=company_id, **{k: data.get(k) for k in [
        "name", "source_server_id", "source_router_id", "target_server_id", "target_router_id", "link_type", "bandwidth_mbps"
    ] if data.get(k) is not None})
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


@router.delete("/links/{link_id}")
def delete_link(
    link_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    link = session.get(NetworkLink, link_id)
    if not link or link.company_id != company_id:
        raise HTTPException(404)
    session.delete(link)
    session.commit()
    return {"ok": True}


@router.put("/positions")
def save_positions(
    positions: list[dict],
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    for p in positions:
        node_type = p.get("node_type")
        node_id = p.get("node_id")
        x, y = p.get("position_x", 0), p.get("position_y", 0)
        existing = session.exec(select(NodePosition).where(
            NodePosition.company_id == company_id,
            NodePosition.node_type == node_type,
            NodePosition.node_id == node_id
        )).first()
        if existing:
            existing.position_x = x
            existing.position_y = y
        else:
            session.add(NodePosition(company_id=company_id, node_type=node_type, node_id=node_id, position_x=x, position_y=y))
    session.commit()
    return {"ok": True}
