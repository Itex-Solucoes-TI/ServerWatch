from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.deps import get_session, get_company_id, require_role
from app.models.server import Server
from app.models.docker_snapshot import DockerSnapshot
from app.services.docker_service import _sync_server, get_docker_client, _close_client

router = APIRouter(prefix="/docker", tags=["docker"])


def _get_server(session: Session, server_id: int, company_id: int) -> Server:
    srv = session.get(Server, server_id)
    if not srv or srv.company_id != company_id:
        raise HTTPException(404)
    return srv


@router.get("/servers/{server_id}/containers")
def list_containers(
    server_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    _get_server(session, server_id, company_id)
    return session.exec(select(DockerSnapshot).where(DockerSnapshot.server_id == server_id)).all()


@router.post("/servers/{server_id}/sync")
def sync_containers(
    server_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    srv = _get_server(session, server_id, company_id)
    try:
        _sync_server(srv, session)
        session.commit()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(503, str(e) or "Erro ao conectar ao Docker")


@router.post("/servers/{server_id}/containers/{container_id}/start")
def start_container(
    server_id: int,
    container_id: str,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    srv = _get_server(session, server_id, company_id)
    client = get_docker_client(srv)
    try:
        c = client.containers.get(container_id)
        c.start()
        return {"ok": True}
    finally:
        _close_client(client)


@router.post("/servers/{server_id}/containers/{container_id}/stop")
def stop_container(
    server_id: int,
    container_id: str,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    srv = _get_server(session, server_id, company_id)
    client = get_docker_client(srv)
    try:
        c = client.containers.get(container_id)
        c.stop()
        return {"ok": True}
    finally:
        _close_client(client)


@router.post("/servers/{server_id}/containers/{container_id}/restart")
def restart_container(
    server_id: int,
    container_id: str,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    srv = _get_server(session, server_id, company_id)
    client = get_docker_client(srv)
    try:
        c = client.containers.get(container_id)
        c.restart()
        return {"ok": True}
    finally:
        _close_client(client)


@router.delete("/servers/{server_id}/containers/{container_id}")
def remove_container(
    server_id: int,
    container_id: str,
    force: bool = False,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    srv = _get_server(session, server_id, company_id)
    client = get_docker_client(srv)
    try:
        c = client.containers.get(container_id)
        c.remove(force=force)
        for snap in session.exec(select(DockerSnapshot).where(DockerSnapshot.server_id == server_id, DockerSnapshot.container_id == container_id)).all():
            session.delete(snap)
        session.commit()
        return {"ok": True}
    finally:
        _close_client(client)
