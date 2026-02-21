"""
Check SNMP: verifica um threshold de métrica SNMP para um roteador.
Target format: "ROUTER_ID:METRIC_TYPE[:THRESHOLD_OPERATOR:VALUE]"
Exemplos:
  "42:CPU" -> consulta última leitura de CPU do roteador 42
  "42:CPU:>:90" -> alerta se CPU > 90%
  "42:MEMORY:>:85"
  "42:WIFI_CLIENTS:>:50"
"""
from datetime import datetime, timedelta
from app.models.health_check import HealthCheck, CheckResult


def check(hc: HealthCheck) -> CheckResult | None:
    try:
        return _check(hc)
    except Exception as e:
        return CheckResult(
            check_id=hc.id,
            status="ERROR",
            latency_ms=None,
            message=str(e)[:255],
            checked_at=datetime.utcnow(),
        )


def _check(hc: HealthCheck) -> CheckResult | None:
    from sqlmodel import Session, select
    from app.database import engine
    from app.models.snmp_metric import SnmpMetric

    target = (hc.target or "").strip()
    parts = target.split(":")
    if len(parts) < 2:
        return CheckResult(check_id=hc.id, status="ERROR", latency_ms=None,
                           message="Target inválido. Formato: ROUTER_ID:METRIC_TYPE[:OP:VALOR]",
                           checked_at=datetime.utcnow())

    router_id = int(parts[0])
    metric_type = parts[1].upper()
    threshold_op = parts[2] if len(parts) > 2 else None
    threshold_val = float(parts[3]) if len(parts) > 3 else None

    with Session(engine) as session:
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        last = session.exec(
            select(SnmpMetric).where(
                SnmpMetric.router_id == router_id,
                SnmpMetric.metric_type == metric_type,
                SnmpMetric.collected_at >= cutoff,
            ).order_by(SnmpMetric.collected_at.desc()).limit(1)
        ).first()

    if not last:
        return CheckResult(check_id=hc.id, status="UNKNOWN", latency_ms=None,
                           message=f"Sem dados SNMP recentes para roteador {router_id} / {metric_type}",
                           checked_at=datetime.utcnow())

    value = last.value
    status = "OK"
    msg = f"{metric_type} = {value} {last.unit}"

    if threshold_op and threshold_val is not None:
        breached = (
            (threshold_op == ">" and value > threshold_val) or
            (threshold_op == ">=" and value >= threshold_val) or
            (threshold_op == "<" and value < threshold_val) or
            (threshold_op == "<=" and value <= threshold_val) or
            (threshold_op == "==" and value == threshold_val)
        )
        if breached:
            status = "FAIL"
            msg = f"ALERTA: {metric_type} = {value} {last.unit} ({threshold_op} {threshold_val})"

    return CheckResult(
        check_id=hc.id,
        status=status,
        latency_ms=None,
        message=msg if status != "OK" else None,
        checked_at=datetime.utcnow(),
    )
