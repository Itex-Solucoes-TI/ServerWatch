import time
from sqlalchemy import create_engine, text
from app.models.health_check import HealthCheck, CheckResult


def check(hc: HealthCheck) -> CheckResult:
    start = time.monotonic()
    try:
        engine = create_engine(hc.target, connect_args={"connect_timeout": hc.timeout_sec})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = int((time.monotonic() - start) * 1000)
        return CheckResult(check_id=hc.id, status="OK", latency_ms=latency)
    except Exception as e:
        return CheckResult(check_id=hc.id, status="ERROR", message=str(e)[:200])
