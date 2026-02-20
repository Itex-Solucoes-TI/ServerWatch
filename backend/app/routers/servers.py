from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select
from app.deps import get_session, get_company_id, require_role
from app.models.server import Server
from app.models.network_interface import NetworkInterface
from app.schemas.server import ServerCreate, ServerUpdate, ServerRead, NetworkInterfaceCreate
from app.services.audit_service import log

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("", response_model=list[ServerRead])
def list_servers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    items = session.exec(select(Server).where(Server.company_id == company_id, Server.active == True).offset(skip).limit(limit)).all()
    return items


@router.post("", response_model=ServerRead)
def create_server(
    data: ServerCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    s = Server(company_id=company_id, **data.model_dump())
    session.add(s)
    log(session, user.id, "CREATE", company_id, "SERVER", None)
    session.commit()
    session.refresh(s)
    return s


@router.get("/{id}", response_model=ServerRead)
def get_server(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    s = session.get(Server, id)
    if not s or s.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    return s


@router.put("/{id}", response_model=ServerRead)
def update_server(
    id: int,
    data: ServerUpdate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    s = session.get(Server, id)
    if not s or s.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    log(session, user.id, "UPDATE", company_id, "SERVER", id)
    session.commit()
    session.refresh(s)
    return s


@router.delete("/{id}")
def delete_server(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    s = session.get(Server, id)
    if not s or s.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    s.active = False
    log(session, user.id, "DELETE", company_id, "SERVER", id)
    session.commit()
    return {"ok": True}


@router.get("/{id}/interfaces")
def list_interfaces(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    s = session.get(Server, id)
    if not s or s.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    items = session.exec(select(NetworkInterface).where(NetworkInterface.server_id == id)).all()
    return items


@router.post("/{id}/interfaces")
def add_interface(
    id: int,
    data: NetworkInterfaceCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    s = session.get(Server, id)
    if not s or s.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    ni = NetworkInterface(server_id=id, **data.model_dump())
    session.add(ni)
    session.commit()
    session.refresh(ni)
    return ni


@router.put("/{server_id}/interfaces/{interface_id}")
def update_interface(
    server_id: int,
    interface_id: int,
    data: NetworkInterfaceCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    s = session.get(Server, server_id)
    if not s or s.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    ni = session.get(NetworkInterface, interface_id)
    if not ni or ni.server_id != server_id:
        raise HTTPException(404, "Não encontrado")
    for k, v in data.model_dump().items():
        setattr(ni, k, v)
    session.add(ni)
    session.commit()
    session.refresh(ni)
    return ni


@router.delete("/{server_id}/interfaces/{interface_id}")
def delete_interface(
    server_id: int,
    interface_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    s = session.get(Server, server_id)
    if not s or s.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    ni = session.get(NetworkInterface, interface_id)
    if not ni or ni.server_id != server_id:
        raise HTTPException(404, "Não encontrado")
    session.delete(ni)
    session.commit()
    return {"ok": True}
