from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from app.deps import get_session, get_company_id, require_role
from app.models.server import Server
from app.models.router import Router
from app.models.health_check import HealthCheck, CheckResult

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    servers = session.exec(select(Server).where(Server.company_id == company_id, Server.active == True)).all()
    routers = session.exec(select(Router).where(Router.company_id == company_id, Router.active == True)).all()
    checks = session.exec(select(HealthCheck).where(HealthCheck.company_id == company_id, HealthCheck.active == True)).all()

    # último resultado de cada check
    last_results: dict[int, CheckResult] = {}
    for c in checks:
        r = session.exec(
            select(CheckResult).where(CheckResult.check_id == c.id).order_by(CheckResult.checked_at.desc()).limit(1)
        ).first()
        if r:
            last_results[c.id] = r

    status_map = {c.id: last_results[c.id].status if c.id in last_results else "UNKNOWN" for c in checks}

    checks_ok = sum(1 for s in status_map.values() if s == "OK")
    checks_fail = sum(1 for s in status_map.values() if s in ("FAIL", "ERROR"))
    checks_unknown = sum(1 for s in status_map.values() if s == "UNKNOWN")

    # latência média das últimas 1h
    since = datetime.utcnow() - timedelta(hours=1)
    latencies = session.exec(
        select(CheckResult.latency_ms).where(
            CheckResult.check_id.in_([c.id for c in checks]),
            CheckResult.checked_at >= since,
            CheckResult.latency_ms != None,
        )
    ).all()
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else None

    # uptime geral últimas 24h (% de resultados OK)
    since_24h = datetime.utcnow() - timedelta(hours=24)
    total_24h = session.exec(
        select(func.count(CheckResult.id)).where(
            CheckResult.check_id.in_([c.id for c in checks]),
            CheckResult.checked_at >= since_24h,
        )
    ).one()
    ok_24h = session.exec(
        select(func.count(CheckResult.id)).where(
            CheckResult.check_id.in_([c.id for c in checks]),
            CheckResult.checked_at >= since_24h,
            CheckResult.status == "OK",
        )
    ).one()
    uptime_pct = round((ok_24h / total_24h) * 100, 1) if total_24h else None

    # checks com pior latência (top 5)
    slowest = sorted(
        [
            {"check_id": c.id, "name": c.name, "latency_ms": last_results[c.id].latency_ms}
            for c in checks
            if c.id in last_results and last_results[c.id].latency_ms is not None
        ],
        key=lambda x: x["latency_ms"],
        reverse=True,
    )[:5]

    # alertas (não OK) com latência
    alerts = [
        {
            "check_id": c.id,
            "name": c.name,
            "status": status_map.get(c.id, "UNKNOWN"),
            "latency_ms": last_results[c.id].latency_ms if c.id in last_results else None,
            "message": last_results[c.id].message if c.id in last_results else None,
            "checked_at": last_results[c.id].checked_at.isoformat() if c.id in last_results else None,
        }
        for c in checks
        if status_map.get(c.id) != "OK"
    ]

    # distribuição por tipo de check
    check_types: dict[str, int] = {}
    for c in checks:
        check_types[c.check_type] = check_types.get(c.check_type, 0) + 1

    # servidores por ambiente
    env_counts: dict[str, int] = {}
    for s in servers:
        env_counts[s.environment] = env_counts.get(s.environment, 0) + 1

    # Resumo SNMP dos roteadores com monitoramento ativo
    snmp_summary = _snmp_summary(routers, session)

    return {
        "servers_count": len(servers),
        "routers_count": len(routers),
        "checks_count": len(checks),
        "checks_ok": checks_ok,
        "checks_fail": checks_fail,
        "checks_unknown": checks_unknown,
        "avg_latency_ms": avg_latency,
        "uptime_24h_pct": uptime_pct,
        "slowest_checks": slowest,
        "alerts": alerts[:10],
        "check_types": check_types,
        "servers_by_env": env_counts,
        "routers_with_vpn": sum(1 for r in routers if r.has_vpn),
        "snmp_summary": snmp_summary,
    }


def _snmp_summary(routers, session: Session) -> dict:
    """Agrega métricas SNMP recentes para o dashboard."""
    from app.models.snmp_metric import SnmpMetric
    from datetime import timedelta
    monitored_ids = [r.id for r in routers if r.snmp_enabled]
    if not monitored_ids:
        return {"monitored_count": 0, "routers": []}

    # Última leitura de cada (router, type, interface) — sem limite de tempo
    metrics = session.exec(
        select(SnmpMetric).where(
            SnmpMetric.router_id.in_(monitored_ids),
            SnmpMetric.metric_type.in_(["CPU", "MEMORY", "WIFI_CLIENTS", "TRAFFIC_IN", "TRAFFIC_OUT"]),
        ).order_by(SnmpMetric.collected_at.desc())
    ).all()

    seen: dict[tuple, SnmpMetric] = {}
    for m in metrics:
        key = (m.router_id, m.metric_type, m.interface_name)
        if key not in seen:
            seen[key] = m

    router_map = {r.id: r.name for r in routers if r.snmp_enabled}
    summary: dict[int, dict] = {rid: {"router_id": rid, "name": router_map[rid]} for rid in monitored_ids}

    total_clients = 0
    for (rid, mtype, iface), m in seen.items():
        if mtype == "CPU":
            summary[rid]["cpu"] = m.value
        elif mtype == "MEMORY":
            summary[rid]["memory"] = m.value
        elif mtype == "WIFI_CLIENTS":
            summary[rid]["wifi_clients"] = int(m.value)
            total_clients += int(m.value)
        elif mtype == "TRAFFIC_IN":
            summary[rid].setdefault("traffic_in", 0)
            summary[rid]["traffic_in"] += m.value
        elif mtype == "TRAFFIC_OUT":
            summary[rid].setdefault("traffic_out", 0)
            summary[rid]["traffic_out"] += m.value

    # Inclui todos os roteadores com SNMP habilitado, mesmo sem métricas ainda
    router_list = list(summary.values())
    return {
        "monitored_count": len(monitored_ids),
        "total_wifi_clients": total_clients,
        "routers": router_list,
    }
