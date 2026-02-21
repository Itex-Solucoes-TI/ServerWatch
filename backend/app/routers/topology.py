import subprocess
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from jose import jwt, JWTError
from app.deps import get_session, get_company_id, require_role
from app.models.network_link import NetworkLink
from app.models.node_position import NodePosition
from app.models.generic_device import GenericDevice
from app.models.user import User, UserCompanyRole
from app.services.topology_service import get_graph
from app.config import settings

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
    allowed = [
        "name", "link_type", "bandwidth_mbps",
        "source_server_id", "source_router_id", "source_generic_id",
        "target_server_id", "target_router_id", "target_generic_id",
    ]
    link = NetworkLink(company_id=company_id, **{k: data.get(k) for k in allowed if data.get(k) is not None})
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


# --- GenericDevice CRUD ---

_CAMERA_FIELDS = ("name", "device_type", "ip_address", "notes", "rtsp_username", "rtsp_password", "rtsp_port", "rtsp_channel", "rtsp_subtype")


@router.get("/devices/{dev_id}")
def get_device(
    dev_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    dev = session.get(GenericDevice, dev_id)
    if not dev or dev.company_id != company_id:
        raise HTTPException(404)
    return dev


@router.get("/devices")
def list_devices(
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    return session.exec(select(GenericDevice).where(GenericDevice.company_id == company_id, GenericDevice.active == True)).all()


@router.post("/devices")
def create_device(
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    dev = GenericDevice(
        company_id=company_id,
        **{k: data[k] for k in _CAMERA_FIELDS if k in data and data[k] is not None},
    )
    session.add(dev)
    session.commit()
    session.refresh(dev)
    return dev


@router.put("/devices/{dev_id}")
def update_device(
    dev_id: int,
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    dev = session.get(GenericDevice, dev_id)
    if not dev or dev.company_id != company_id:
        raise HTTPException(404)
    for f in _CAMERA_FIELDS:
        if f in data:
            setattr(dev, f, data[f])
    session.commit()
    return dev


@router.delete("/devices/{dev_id}")
def delete_device(
    dev_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    dev = session.get(GenericDevice, dev_id)
    if not dev or dev.company_id != company_id:
        raise HTTPException(404)
    dev.active = False
    session.commit()
    return {"ok": True}


# --- Camera MJPEG stream ---

def _build_rtsp_url(dev: GenericDevice) -> str:
    """Gera URL RTSP no padrão Intelbras/Hikvision."""
    user = dev.rtsp_username or ""
    pwd = dev.rtsp_password or ""
    auth = f"{user}:{pwd}@" if user else ""
    port = dev.rtsp_port or 554
    channel = dev.rtsp_channel or 1
    subtype = dev.rtsp_subtype if dev.rtsp_subtype is not None else 0
    return f"rtsp://{auth}{dev.ip_address}:{port}/cam/realmonitor?channel={channel}&subtype={subtype}"


def _mjpeg_generator(rtsp_url: str):
    """Converte RTSP para MJPEG usando ffmpeg."""
    cmd = [
        "ffmpeg", "-loglevel", "quiet",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-vf", "scale=640:-1",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "-q:v", "5",
        "-r", "10",
        "pipe:1",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
    buf = b""
    try:
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            buf += chunk
            start = buf.find(b"\xff\xd8")
            end = buf.find(b"\xff\xd9")
            while start != -1 and end != -1 and end > start:
                frame = buf[start:end + 2]
                buf = buf[end + 2:]
                yield boundary + frame + b"\r\n"
                start = buf.find(b"\xff\xd8")
                end = buf.find(b"\xff\xd9")
    finally:
        proc.kill()


@router.get("/devices/{dev_id}/stream")
def camera_stream(
    dev_id: int,
    token: str = Query(...),
    company_id: int = Query(..., alias="cid"),
    session: Session = Depends(get_session),
):
    """Endpoint de stream MJPEG — autenticação via query param (necessário para tag <img>)."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise HTTPException(403)
        user = session.get(User, payload["user_id"])
        if not user or not user.active:
            raise HTTPException(403)
        if not user.is_superadmin:
            role = session.exec(
                select(UserCompanyRole)
                .where(UserCompanyRole.user_id == user.id)
                .where(UserCompanyRole.company_id == company_id)
            ).first()
            if not role:
                raise HTTPException(403)
    except JWTError:
        raise HTTPException(403)

    dev = session.get(GenericDevice, dev_id)
    if not dev or dev.company_id != company_id or dev.device_type != "CAMERA":
        raise HTTPException(404)
    if not dev.ip_address:
        raise HTTPException(400, "IP não configurado")
    rtsp_url = _build_rtsp_url(dev)
    return StreamingResponse(
        _mjpeg_generator(rtsp_url),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
