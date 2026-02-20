import httpx
import time
from app.models.health_check import HealthCheck, CheckResult


def check(hc: HealthCheck) -> CheckResult:
    start = time.monotonic()
    try:
        r = httpx.get(hc.target, timeout=hc.timeout_sec, follow_redirects=True)
        latency = int((time.monotonic() - start) * 1000)
        expected = hc.expected_status or 200
        ok = r.status_code == expected
        return CheckResult(check_id=hc.id, status="OK" if ok else "ERROR", latency_ms=latency, message=f"HTTP {r.status_code}")
    except Exception as e:
        return CheckResult(check_id=hc.id, status="ERROR", message=str(e)[:200])
