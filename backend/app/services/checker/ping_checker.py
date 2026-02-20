import os
import subprocess
import time
import re
from app.models.health_check import HealthCheck, CheckResult

PING_BIN = "/usr/bin/ping" if os.path.exists("/usr/bin/ping") else ("/bin/ping" if os.path.exists("/bin/ping") else "ping")


def check(hc: HealthCheck) -> CheckResult:
    start = time.monotonic()
    try:
        result = subprocess.run(
            [PING_BIN, "-c", "1", "-W", str(hc.timeout_sec), hc.target],
            capture_output=True, text=True, timeout=hc.timeout_sec + 2
        )
        latency = int((time.monotonic() - start) * 1000)
        if result.returncode == 0:
            match = re.search(r"time=([\d.]+)", result.stdout)
            ms = int(float(match.group(1))) if match else latency
            return CheckResult(check_id=hc.id, status="OK", latency_ms=ms)
        return CheckResult(check_id=hc.id, status="ERROR", message="Host unreachable")
    except FileNotFoundError:
        return CheckResult(check_id=hc.id, status="ERROR", message="ping não encontrado. Use 'Executar via SSH' ou instale iputils no container.")
    except Exception as e:
        return CheckResult(check_id=hc.id, status="ERROR", message=str(e)[:200])
