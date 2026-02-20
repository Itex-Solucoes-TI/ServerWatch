import socket
import time
from app.models.health_check import HealthCheck, CheckResult


def check(hc: HealthCheck) -> CheckResult:
    host, port = hc.target.rsplit(":", 1)
    start = time.monotonic()
    try:
        with socket.create_connection((host, int(port)), timeout=hc.timeout_sec):
            latency = int((time.monotonic() - start) * 1000)
            return CheckResult(check_id=hc.id, status="OK", latency_ms=latency)
    except socket.timeout:
        return CheckResult(check_id=hc.id, status="TIMEOUT", message="Connection timed out")
    except Exception as e:
        return CheckResult(check_id=hc.id, status="ERROR", message=str(e)[:200])
