from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select
from app.deps import get_session, get_company_id, require_role
from app.models.router import Router
from app.models.network_interface import NetworkInterface
from app.schemas.router import RouterCreate, RouterUpdate, RouterRead
from app.schemas.server import NetworkInterfaceCreate
from app.services.audit_service import log

router = APIRouter(prefix="/routers", tags=["routers"])


@router.get("", response_model=list[RouterRead])
def list_routers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    items = session.exec(select(Router).where(Router.company_id == company_id, Router.active == True).offset(skip).limit(limit)).all()
    return items


@router.post("", response_model=RouterRead)
def create_router(
    data: RouterCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = Router(company_id=company_id, **data.model_dump())
    session.add(r)
    log(session, user.id, "CREATE", company_id, "ROUTER", None)
    session.commit()
    session.refresh(r)
    return r


@router.get("/{id}", response_model=RouterRead)
def get_router(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    return r


@router.put("/{id}", response_model=RouterRead)
def update_router(
    id: int,
    data: RouterUpdate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    log(session, user.id, "UPDATE", company_id, "ROUTER", id)
    session.commit()
    session.refresh(r)
    return r


@router.delete("/{id}")
def delete_router(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    r.active = False
    log(session, user.id, "DELETE", company_id, "ROUTER", id)
    session.commit()
    return {"ok": True}


@router.get("/{id}/interfaces")
def list_interfaces(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    items = session.exec(select(NetworkInterface).where(NetworkInterface.router_id == id)).all()
    return items


@router.post("/{id}/interfaces")
def add_interface(
    id: int,
    data: NetworkInterfaceCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    ni = NetworkInterface(router_id=id, **data.model_dump())
    session.add(ni)
    session.commit()
    session.refresh(ni)
    return ni


@router.put("/{id}/interfaces/{interface_id}")
def update_interface(
    id: int,
    interface_id: int,
    data: NetworkInterfaceCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    ni = session.get(NetworkInterface, interface_id)
    if not ni or ni.router_id != id:
        raise HTTPException(404, "Não encontrado")
    for k, v in data.model_dump().items():
        setattr(ni, k, v)
    session.add(ni)
    session.commit()
    session.refresh(ni)
    return ni


@router.delete("/{id}/interfaces/{interface_id}")
def delete_interface(
    id: int,
    interface_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    ni = session.get(NetworkInterface, interface_id)
    if not ni or ni.router_id != id:
        raise HTTPException(404, "Não encontrado")
    session.delete(ni)
    session.commit()
    return {"ok": True}
