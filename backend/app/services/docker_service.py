import os
import socket
import subprocess
import tempfile
import time
from sqlmodel import Session, select
from app.database import engine
from app.models.server import Server
from app.models.docker_snapshot import DockerSnapshot
import docker
from docker.tls import TLSConfig
from datetime import datetime

try:
    from sshtunnel import SSHTunnelForwarder
except ImportError:
    SSHTunnelForwarder = None


def _ssh_process_tunnel(server: Server):
    """Túnel via ssh -L (método nativo, mais confiável)."""
    port = _find_free_port()
    env = os.environ.copy()
    if server.ssh_password:
        env["SSHPASS"] = server.ssh_password
        cmd = [
            "sshpass", "-e",
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-N", "-L", f"127.0.0.1:{port}:127.0.0.1:2375",
            "-p", str(server.ssh_port or 22),
            f"{server.ssh_user}@{server.ssh_host}",
        ]
    else:
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-N", "-L", f"127.0.0.1:{port}:127.0.0.1:2375",
            "-p", str(server.ssh_port or 22),
            f"{server.ssh_user}@{server.ssh_host}",
        ]
    proc = subprocess.Popen(
        cmd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)  # aguardar túnel estabilizar
    if proc.poll() is not None:
        raise RuntimeError("SSH tunnel exited immediately")
    return proc, port


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get_docker_client(server: Server):
    if server.ssh_host and server.ssh_user:
        if server.ssh_password:
            try:
                proc, port = _ssh_process_tunnel(server)
                host = f"tcp://127.0.0.1:{port}"
                client = docker.DockerClient(base_url=host, version="1.41", timeout=60)
                client._ssh_proc = proc
                return client
            except Exception:
                pass
        if SSHTunnelForwarder:
            tunnel = SSHTunnelForwarder(
                (server.ssh_host, server.ssh_port or 22),
                ssh_username=server.ssh_user,
                ssh_password=server.ssh_password or None,
                remote_bind_address=("127.0.0.1", 2375),
                local_bind_address=("127.0.0.1", 0),
                allow_agent=False,
            )
            tunnel.start()
            host = f"tcp://127.0.0.1:{tunnel.local_bind_port}"
            client = docker.DockerClient(base_url=host, version="1.41", timeout=60)
            client._ssh_tunnel = tunnel
            return client
    host = server.docker_host or "unix:///var/run/docker.sock"
    tls_config = None
    tmp_files = []
    if server.docker_tls_ca_cert or (server.docker_tls_client_cert and server.docker_tls_client_key):
        try:
            ca_path = cert_path = key_path = None
            if server.docker_tls_ca_cert:
                f = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
                f.write(server.docker_tls_ca_cert)
                f.close()
                ca_path = f.name
                tmp_files.append(ca_path)
            if server.docker_tls_client_cert:
                f = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
                f.write(server.docker_tls_client_cert)
                f.close()
                cert_path = f.name
                tmp_files.append(cert_path)
            if server.docker_tls_client_key:
                f = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
                f.write(server.docker_tls_client_key)
                f.close()
                key_path = f.name
                tmp_files.append(key_path)
            tls_kw = {}
            if ca_path:
                tls_kw["ca_cert"] = ca_path
                tls_kw["verify"] = True
            if cert_path and key_path:
                tls_kw["client_cert"] = (cert_path, key_path)
            tls_config = TLSConfig(**tls_kw)
            if host.startswith("tcp://"):
                host = host.replace("tcp://", "https://", 1).replace(":2375", ":2376")
        except Exception:
            for p in tmp_files:
                try:
                    os.unlink(p)
                except OSError:
                    pass
            raise
    client = docker.DockerClient(base_url=host, tls=tls_config)
    if tmp_files:
        client._tmp_cert_files = tmp_files
    return client


def get_docker_client(server: Server) -> docker.DockerClient:
    return _get_docker_client(server)


def _close_client(client):
    try:
        client.close()
    except Exception:
        pass
    tunnel = getattr(client, "_ssh_tunnel", None)
    if tunnel:
        try:
            tunnel.stop()
        except Exception:
            pass
    proc = getattr(client, "_ssh_proc", None)
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    for p in getattr(client, "_tmp_cert_files", []):
        try:
            os.unlink(p)
        except OSError:
            pass


def sync_all_docker():
    with Session(engine) as session:
        servers = session.exec(
            select(Server).where(Server.has_docker == True)
        ).all()
        for srv in servers:
            try:
                _sync_server(srv, session)
            except Exception:
                pass
        session.commit()


def _sync_server(server: Server, session: Session):
    client = _get_docker_client(server)
    try:
        containers = client.containers.list(all=True)
        existing_ids = set()
        for c in containers:
            short_id = c.short_id
            existing_ids.add(short_id)
            cpu = mem_pct = mem_mb = None
            old = session.exec(select(DockerSnapshot).where(DockerSnapshot.server_id == server.id, DockerSnapshot.container_id == short_id)).first()
            if old:
                old.name = c.name
                old.image = c.image.tags[0] if c.image.tags else str(c.image)
                old.status = c.status
                old.cpu_percent = cpu
                old.mem_percent = mem_pct
                old.mem_usage_mb = mem_mb
                old.synced_at = datetime.utcnow()
            else:
                session.add(DockerSnapshot(
                    server_id=server.id,
                    container_id=short_id,
                    name=c.name,
                    image=c.image.tags[0] if c.image.tags else str(c.image),
                    status=c.status,
                    cpu_percent=cpu,
                    mem_percent=mem_pct,
                    mem_usage_mb=mem_mb,
                ))
        for snap in session.exec(select(DockerSnapshot).where(DockerSnapshot.server_id == server.id)).all():
            if snap.container_id not in existing_ids:
                session.delete(snap)
    finally:
        _close_client(client)
