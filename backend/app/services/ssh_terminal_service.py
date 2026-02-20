"""
Proxy WebSocket <-> SSH. Recebe dados do browser, envia ao canal SSH;
recebe do canal SSH, envia ao browser.
"""
import asyncio
import queue
import socket
import threading
from jose import jwt, JWTError
from sqlmodel import Session, select
import paramiko

from app.config import settings
from app.database import engine
from app.models.server import Server
from app.models.user import User
from app.models.user import UserCompanyRole


def _verify_ws_token(token: str, company_id: int) -> User | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        with Session(engine) as session:
            user = session.get(User, payload["user_id"])
            if not user or not user.active:
                return None
            if user.is_superadmin:
                return user
            role = session.exec(
                select(UserCompanyRole).where(
                    UserCompanyRole.user_id == user.id,
                    UserCompanyRole.company_id == company_id,
                )
            ).first()
            if not role or role.role not in ("ADMIN", "OPERATOR", "VIEWER"):
                return None
            return user
    except JWTError:
        return None


def run_ssh_bridge(
    server: Server,
    out_queue: queue.Queue,
    in_queue: queue.Queue,
    closed: threading.Event,
):
    """Thread: conecta SSH, bridge in_queue -> channel, channel -> out_queue."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    chan = None
    try:
        client.connect(
            hostname=server.ssh_host,
            port=server.ssh_port or 22,
            username=server.ssh_user,
            password=server.ssh_password or None,
            timeout=10,
        )
        chan = client.get_transport().open_session()
        chan.get_pty()
        chan.invoke_shell()
        chan.settimeout(0.1)
        while not closed.is_set():
            while not in_queue.empty():
                try:
                    data = in_queue.get_nowait()
                    if data is None:
                        break
                    chan.send(data)
                except queue.Empty:
                    break
            try:
                data = chan.recv(4096)
                if data:
                    out_queue.put(data.decode("utf-8", errors="replace"))
                else:
                    break
            except (socket.timeout, paramiko.SSHException):
                pass
    except (socket.timeout, paramiko.SSHException, OSError):
        pass
    except Exception as e:
        try:
            out_queue.put(f"\r\n\r\n*** SSH error: {e} ***\r\n")
        except Exception:
            pass
    finally:
        if chan:
            chan.close()
        client.close()
        out_queue.put(None)
