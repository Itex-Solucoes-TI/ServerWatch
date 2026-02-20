"""
Executa Health Checks via SSH no servidor remoto.
Usa paramiko para exec_command. Suporta PING, PORT, URL, TELNET.
DATABASE não suportado via SSH (cai no checker local).
"""
import time
import paramiko
from app.models.health_check import HealthCheck, CheckResult
from app.models.server import Server


def _run_ssh(server: Server, cmd: str, timeout: int) -> tuple[int, str, str]:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=server.ssh_host,
            port=server.ssh_port or 22,
            username=server.ssh_user,
            password=server.ssh_password or None,
            timeout=timeout,
        )
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        code = stdout.channel.recv_exit_status()
        return code, stdout.read().decode(errors="ignore"), stderr.read().decode(errors="ignore")
    finally:
        client.close()


def check(hc: HealthCheck, server: Server) -> CheckResult:
    if hc.check_type == "DATABASE":
        return CheckResult(check_id=hc.id, status="ERROR", message="DATABASE não suportado via SSH")
    timeout = min(hc.timeout_sec, 30)
    start = time.monotonic()
    cmd = _build_cmd(hc, timeout)
    if not cmd:
        return CheckResult(check_id=hc.id, status="ERROR", message="Tipo de check inválido")
    try:
        code, out, err = _run_ssh(server, cmd, timeout + 5)
        latency = int((time.monotonic() - start) * 1000)
        return _parse_result(hc, code, out, err, latency)
    except Exception as e:
        return CheckResult(check_id=hc.id, status="ERROR", message=str(e)[:200])


def _build_cmd(hc: HealthCheck, timeout: int) -> str | None:
    t = str(timeout)
    if hc.check_type == "PING":
        return f"ping -c 1 -W {t} {hc.target}"
    if hc.check_type in ("PORT", "TELNET"):
        parts = hc.target.rsplit(":", 1)
        if len(parts) != 2:
            return None
        host, port = parts
        return f"timeout {t} nc -zv {host} {port} 2>/dev/null || timeout {t} bash -c 'echo >/dev/tcp/{host}/{port}' 2>/dev/null"
    if hc.check_type == "URL":
        return f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout {t} --max-time {int(timeout)+5} '{hc.target}'"
    return None


def _parse_result(hc: HealthCheck, code: int, out: str, err: str, latency: int) -> CheckResult:
    msg = (out or err or "").strip()[:200]
    if hc.check_type == "PING":
        if code == 0:
            return CheckResult(check_id=hc.id, status="OK", latency_ms=latency)
        return CheckResult(check_id=hc.id, status="ERROR", latency_ms=latency, message=msg or "Host unreachable")
    if hc.check_type in ("PORT", "TELNET"):
        if code == 0:
            return CheckResult(check_id=hc.id, status="OK", latency_ms=latency)
        return CheckResult(check_id=hc.id, status="ERROR" if "timed out" in msg.lower() else "ERROR", latency_ms=latency, message=msg or "Connection failed")
    if hc.check_type == "URL":
        status_code = out.strip()
        expected = str(hc.expected_status or 200)
        ok = status_code == expected
        return CheckResult(check_id=hc.id, status="OK" if ok else "ERROR", latency_ms=latency, message=f"HTTP {status_code}")
    return CheckResult(check_id=hc.id, status="ERROR", message=msg)
