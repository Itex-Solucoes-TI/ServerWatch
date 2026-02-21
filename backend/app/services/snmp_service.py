"""Coleta informações via SNMP: info básica e métricas dinâmicas."""
import asyncio
import concurrent.futures
from datetime import datetime, timedelta
from app.services.snmp_oids import OIDS_INFO, OIDS_INTERFACES, OIDS_CPU, OIDS_MEMORY

_BASIC_OIDS = {k: v for k, v in OIDS_INFO.items()}


def _run_async(coro):
    """Executa uma coroutine em thread separada com event loop próprio.
    Funciona tanto no scheduler (BackgroundScheduler/threads) quanto no FastAPI (uvicorn asyncio).
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run_in_new_loop, coro)
        return future.result(timeout=30)


def _run_in_new_loop(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def get_info(host: str, community: str = "public", port: int = 161, timeout: int = 10) -> dict:
    """Obtém informações básicas do dispositivo via SNMP v2c GET."""
    host = _clean_host(host)
    if not host:
        return {"error": "Host/IP inválido", "target": None}
    target = f"{host}:{port}"
    try:
        return _run_async(_get_info_async(host, community, port, timeout, target))
    except ImportError as e:
        return {"error": f"pysnmp não instalado: {e}", "target": target}
    except Exception as e:
        return {"error": f"{str(e)[:180]} (destino: {target})", "target": target}


def run_snmp_collection():
    """Executado pelo scheduler: coleta métricas de todos os monitores ativos."""
    from sqlmodel import Session, select
    from app.database import engine
    from app.models.snmp_monitor import SnmpMonitor
    from app.models.router import Router

    with Session(engine) as session:
        monitors = session.exec(
            select(SnmpMonitor).where(SnmpMonitor.active == True)
        ).all()
        if not monitors:
            return

        router_ids = list({m.router_id for m in monitors})
        routers = {
            r.id: r for r in session.exec(
                select(Router).where(Router.id.in_(router_ids), Router.snmp_enabled == True)
            ).all()
        }

        for monitor in monitors:
            router = routers.get(monitor.router_id)
            if not router:
                continue
            host = _get_router_host(router.id, session)
            if not host:
                continue
            community = (router.snmp_community or "public").strip() or "public"
            port = router.snmp_port or 161
            _collect_monitor(monitor, host, community, port, session)


# ---------------------------------------------------------------------------
# Coleta por tipo de monitor
# ---------------------------------------------------------------------------

def _collect_monitor(monitor, host: str, community: str, port: int, session):
    from app.models.snmp_metric import SnmpMetric

    try:
        metrics: list[SnmpMetric] = []
        if monitor.metric_type in ("TRAFFIC", "TRAFFIC_IN", "TRAFFIC_OUT"):
            metrics = _collect_traffic_sync(monitor, host, community, port, session)
        elif monitor.metric_type == "CPU":
            metrics = _run_async(_collect_cpu(monitor, host, community, port))
        elif monitor.metric_type == "MEMORY":
            metrics = _run_async(_collect_memory(monitor, host, community, port))
        elif monitor.metric_type == "WIFI_CLIENTS":
            metrics = _run_async(_collect_wifi_clients(monitor, host, community, port))
        elif monitor.metric_type == "UPTIME":
            metrics = _run_async(_collect_uptime(monitor, host, community, port))

        for m in metrics:
            session.add(m)
        if metrics:
            session.commit()

        # Verifica threshold e sincroniza health check vinculado ao roteador
        if metrics and monitor.threshold_warn is not None:
            value_metrics = [m for m in metrics if m.metric_type not in ("TRAFFIC_RAW_IN", "TRAFFIC_RAW_OUT")]
            if value_metrics:
                _sync_snmp_health_check(monitor, value_metrics[0], session)

        try:
            from app.services.ws_manager import broadcast_check_update
        except Exception:
            pass
    except Exception:
        pass


def _sync_snmp_health_check(monitor, metric, session):
    """Cria ou atualiza automaticamente um HealthCheck vinculado ao monitor SNMP."""
    from sqlmodel import select
    from app.models.health_check import HealthCheck, CheckResult
    from app.models.router import Router
    from datetime import datetime

    router = session.get(Router, monitor.router_id)
    if not router:
        return

    # Busca check existente vinculado a este monitor (por nome único)
    check_name = f"SNMP {monitor.metric_type} — {router.name}"
    existing = session.exec(
        select(HealthCheck).where(
            HealthCheck.router_id == monitor.router_id,
            HealthCheck.check_type == "SNMP",
            HealthCheck.name == check_name,
        )
    ).first()

    # Target: ROUTER_ID:METRIC_TYPE:OP:THRESHOLD
    target = f"{router.id}:{monitor.metric_type}:>:{monitor.threshold_warn}"

    if not existing:
        existing = HealthCheck(
            company_id=router.company_id,
            router_id=router.id,
            name=check_name,
            check_type="SNMP",
            target=target,
            interval_sec=monitor.interval_sec,
            timeout_sec=10,
            active=True,
        )
        session.add(existing)
        session.commit()
        session.refresh(existing)
    else:
        existing.target = target
        existing.active = True
        session.add(existing)
        session.commit()

    # Avalia o threshold e gera CheckResult
    breached = metric.value > monitor.threshold_warn
    status = "FAIL" if breached else "OK"
    msg = f"{monitor.metric_type} = {metric.value} {metric.unit}" + (f" (alerta >= {monitor.threshold_warn})" if breached else "")

    result = CheckResult(
        check_id=existing.id,
        status=status,
        latency_ms=None,
        message=msg,
        checked_at=datetime.utcnow(),
    )
    existing.last_checked_at = datetime.utcnow()
    session.add(result)
    session.add(existing)
    session.commit()

    # Dispara notificações se configurado
    try:
        from app.services.notification_service import evaluate_alerts
        evaluate_alerts(existing, result, session)
    except Exception:
        pass


def _collect_traffic_sync(monitor, host: str, community: str, port: int, session) -> list:
    """Wrapper sync: coleta SNMP em thread, depois calcula rate com a session."""
    from app.models.snmp_metric import SnmpMetric

    now = datetime.utcnow()

    if monitor.custom_oid:
        raw_val = _run_async(_get_single(host, community, port, monitor.custom_oid))
        val = _as_float(raw_val)
        if val is None:
            return []
        label = monitor.interface_filter or monitor.custom_oid
        if monitor.metric_type == "TRAFFIC_OUT" or ".16." in monitor.custom_oid or "OutOctets" in monitor.custom_oid:
            mtype = "TRAFFIC_OUT"
        else:
            mtype = "TRAFFIC_IN"
        rate = _calc_rate(session, monitor.router_id, mtype, label, val, now)
        if rate is None:
            return []
        return [SnmpMetric(router_id=monitor.router_id, metric_type=mtype, interface_name=label, value=rate, unit="bytes_sec", collected_at=now)]

    # WALK em todas as interfaces
    oid_descr = OIDS_INTERFACES["ifDescr"]
    oid_in = OIDS_INTERFACES["ifInOctets"]
    oid_out = OIDS_INTERFACES["ifOutOctets"]
    iface_descr = _run_async(_walk(host, community, port, oid_descr))
    iface_in = _run_async(_walk(host, community, port, oid_in))
    iface_out = _run_async(_walk(host, community, port, oid_out))

    result = []
    for idx, descr in iface_descr.items():
        if monitor.interface_filter and monitor.interface_filter.lower() not in descr.lower():
            continue
        in_val = _as_float(iface_in.get(idx))
        out_val = _as_float(iface_out.get(idx))
        if in_val is None or out_val is None:
            continue
        rate_in = _calc_rate(session, monitor.router_id, "TRAFFIC_IN", descr, in_val, now)
        rate_out = _calc_rate(session, monitor.router_id, "TRAFFIC_OUT", descr, out_val, now)
        if rate_in is not None:
            result.append(SnmpMetric(router_id=monitor.router_id, metric_type="TRAFFIC_IN", interface_name=descr, value=rate_in, unit="bytes_sec", collected_at=now))
        if rate_out is not None:
            result.append(SnmpMetric(router_id=monitor.router_id, metric_type="TRAFFIC_OUT", interface_name=descr, value=rate_out, unit="bytes_sec", collected_at=now))
    return result


async def _collect_traffic(monitor, host: str, community: str, port: int, session) -> list:
    """
    Coleta tráfego. Suporta 3 modos:
    - TRAFFIC_IN com custom_oid (OID folha ex: 1.3.6.1.2.1.2.2.1.10.1): GET direto, métrica IN
    - TRAFFIC_OUT com custom_oid (OID folha ex: 1.3.6.1.2.1.2.2.1.16.1): GET direto, métrica OUT
    - TRAFFIC sem custom_oid: WALK em todas as interfaces
    """
    from app.models.snmp_metric import SnmpMetric

    now = datetime.utcnow()
    result = []

    # Modo: OID customizado com índice (GET direto numa interface específica)
    if monitor.custom_oid:
        label = monitor.interface_filter or monitor.custom_oid
        raw_val = await _get_single(host, community, port, monitor.custom_oid)
        val = _as_float(raw_val)
        if val is not None:
            # Determina se é IN ou OUT pelo tipo do monitor ou pelo OID
            if monitor.metric_type == "TRAFFIC_OUT" or "1.16" in monitor.custom_oid or "OutOctets" in monitor.custom_oid:
                mtype = "TRAFFIC_OUT"
            else:
                mtype = "TRAFFIC_IN"
            rate = _calc_rate(session, monitor.router_id, mtype, label, val, now)
            if rate is not None:
                result.append(SnmpMetric(router_id=monitor.router_id, metric_type=mtype, interface_name=label, value=rate, unit="bytes_sec", collected_at=now))
        return result

    # Modo: WALK em todas as interfaces (sem OID customizado)
    oid_descr = OIDS_INTERFACES["ifDescr"]
    oid_in = OIDS_INTERFACES["ifInOctets"]
    oid_out = OIDS_INTERFACES["ifOutOctets"]

    iface_descr = await _walk(host, community, port, oid_descr)
    iface_in = await _walk(host, community, port, oid_in)
    iface_out = await _walk(host, community, port, oid_out)

    for idx, descr in iface_descr.items():
        if monitor.interface_filter and monitor.interface_filter.lower() not in descr.lower():
            continue
        raw_in = iface_in.get(idx)
        raw_out = iface_out.get(idx)
        if raw_in is None or raw_out is None:
            continue

        in_val = _as_float(raw_in)
        out_val = _as_float(raw_out)
        if in_val is None or out_val is None:
            continue

        rate_in = _calc_rate(session, monitor.router_id, "TRAFFIC_IN", descr, in_val, now)
        rate_out = _calc_rate(session, monitor.router_id, "TRAFFIC_OUT", descr, out_val, now)

        if rate_in is not None:
            result.append(SnmpMetric(router_id=monitor.router_id, metric_type="TRAFFIC_IN", interface_name=descr, value=rate_in, unit="bytes_sec", collected_at=now))
        if rate_out is not None:
            result.append(SnmpMetric(router_id=monitor.router_id, metric_type="TRAFFIC_OUT", interface_name=descr, value=rate_out, unit="bytes_sec", collected_at=now))

    return result


async def _collect_cpu(monitor, host: str, community: str, port: int) -> list:
    from app.models.snmp_metric import SnmpMetric

    now = datetime.utcnow()
    oid = monitor.custom_oid or OIDS_CPU["hrProcessorLoad"]

    # OID folha (com índice no final): GET direto
    if monitor.custom_oid:
        raw = await _get_single(host, community, port, oid)
        val = _as_float(raw)
        if val is None:
            return []
        return [SnmpMetric(router_id=monitor.router_id, metric_type="CPU", value=round(val, 1), unit="percent", collected_at=now)]

    # OID base: WALK para múltiplos cores
    cores = await _walk(host, community, port, oid)
    if not cores:
        return []
    values = [_as_float(v) for v in cores.values() if _as_float(v) is not None]
    if not values:
        return []
    avg = sum(values) / len(values)
    return [SnmpMetric(router_id=monitor.router_id, metric_type="CPU", value=round(avg, 1), unit="percent", collected_at=now)]


async def _collect_memory(monitor, host: str, community: str, port: int) -> list:
    from app.models.snmp_metric import SnmpMetric

    oid_type = OIDS_MEMORY["hrStorageType"]
    oid_size = OIDS_MEMORY["hrStorageSize"]
    oid_used = OIDS_MEMORY["hrStorageUsed"]
    oid_alloc = OIDS_MEMORY["hrStorageAllocationUnits"]

    types = await _walk(host, community, port, oid_type)
    sizes = await _walk(host, community, port, oid_size)
    used = await _walk(host, community, port, oid_used)
    alloc = await _walk(host, community, port, oid_alloc)

    now = datetime.utcnow()
    for idx, stype in types.items():
        if "ram" not in str(stype).lower() and "1.3.6.1.2.1.25.2.1.2" not in str(stype):
            continue
        sz = _as_float(sizes.get(idx))
        us = _as_float(used.get(idx))
        if sz and us:
            pct = round((us / sz) * 100, 1) if sz else 0
            return [SnmpMetric(router_id=monitor.router_id, metric_type="MEMORY", value=pct, unit="percent", collected_at=now)]
    return []


async def _collect_wifi_clients(monitor, host: str, community: str, port: int) -> list:
    from app.models.snmp_metric import SnmpMetric

    now = datetime.utcnow()
    oid = monitor.custom_oid or "1.3.6.1.4.1.14988.1.1.1.2.1.1"
    entries = await _walk(host, community, port, oid)
    count = len([v for v in entries.values() if v is not None])
    return [SnmpMetric(router_id=monitor.router_id, metric_type="WIFI_CLIENTS", value=count, unit="count", collected_at=now)]


async def _collect_uptime(monitor, host: str, community: str, port: int) -> list:
    from app.models.snmp_metric import SnmpMetric
    from pysnmp.hlapi.asyncio import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity

    oid = monitor.custom_oid or OIDS_INFO["sysUpTime"]
    engine = SnmpEngine()
    transport = UdpTransportTarget((host, port), timeout=5)
    err, err_status, _, var_binds = await getCmd(
        engine, CommunityData(community, mpModel=1), transport, ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )
    if err or err_status or not var_binds:
        return []
    obj_type = var_binds[0]  # getCmd retorna ObjectType diretamente
    ticks = _as_float(str(obj_type[1]))
    if ticks is None:
        return []
    secs = ticks / 100
    return [SnmpMetric(router_id=monitor.router_id, metric_type="UPTIME", value=secs, unit="seconds")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_single(host: str, community: str, port: int, oid: str, timeout: int = 5) -> str | None:
    """GET SNMP de um OID específico (folha), retorna valor como string."""
    from pysnmp.hlapi.asyncio import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
    engine = SnmpEngine()
    transport = UdpTransportTarget((host, port), timeout=timeout)
    err, err_status, _, var_binds = await getCmd(
        engine, CommunityData(community, mpModel=1), transport, ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )
    if err or err_status or not var_binds:
        return None
    obj_type = var_binds[0]  # getCmd retorna ObjectType diretamente
    try:
        val = str(obj_type[1])
    except Exception:
        val = str(obj_type)
    return val if val not in ("No Such Object currently exists at this OID", "No Such Instance") else None


async def _walk(host: str, community: str, port: int, base_oid: str, timeout: int = 5) -> dict:
    """SNMP WALK retorna {índice_sufixo: valor} para o base_oid."""
    from pysnmp.hlapi.asyncio import nextCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity

    result = {}
    engine = SnmpEngine()
    transport = UdpTransportTarget((host, port), timeout=timeout)
    auth = CommunityData(community, mpModel=1)
    ctx = ContextData()
    oid_obj = ObjectType(ObjectIdentity(base_oid))

    while True:
        err, err_status, _, var_binds = await nextCmd(engine, auth, transport, ctx, oid_obj)
        if err or err_status or not var_binds or not var_binds[0]:
            break
        obj_type = var_binds[0][0]
        oid, value = obj_type[0], obj_type[1]
        oid_str = str(oid)
        if not oid_str.startswith(base_oid):
            break
        suffix = oid_str[len(base_oid):].lstrip(".")
        result[suffix] = str(value)
        oid_obj = ObjectType(ObjectIdentity(oid_str))

    return result


def _calc_rate(session, router_id: int, metric_type: str, interface_name: str, current: float, now: datetime) -> float | None:
    """Calcula bytes/s usando a diferença entre coleta atual e anterior."""
    from sqlmodel import select
    from app.models.snmp_metric import SnmpMetric

    last = session.exec(
        select(SnmpMetric).where(
            SnmpMetric.router_id == router_id,
            SnmpMetric.metric_type == "TRAFFIC_RAW_" + metric_type.split("_")[-1],
            SnmpMetric.interface_name == interface_name,
        ).order_by(SnmpMetric.collected_at.desc()).limit(1)
    ).first()

    # Salva valor bruto para próxima coleta (commit imediato)
    raw_type = "TRAFFIC_RAW_" + metric_type.split("_")[-1]
    session.add(SnmpMetric(router_id=router_id, metric_type=raw_type, interface_name=interface_name, value=current, unit="bytes", collected_at=now))
    session.commit()

    if not last:
        return None
    elapsed = (now - last.collected_at).total_seconds()
    if elapsed <= 0 or elapsed > 600:
        return None
    delta = current - last.value
    if delta < 0:
        delta = current  # counter reset
    return round(delta / elapsed, 2)


def _get_router_host(router_id: int, session) -> str | None:
    from sqlmodel import select
    from app.models.network_interface import NetworkInterface
    interfaces = list(session.exec(
        select(NetworkInterface).where(NetworkInterface.router_id == router_id).order_by(NetworkInterface.is_primary.desc())
    ))
    for ni in interfaces:
        ip = _clean_host(ni.ip_address)
        if ip:
            return ip
    return None


def _clean_host(host: str) -> str:
    return (host or "").strip().split("/")[0].split(" ")[0]


def _as_float(v) -> float | None:
    try:
        return float(str(v).split()[0])
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Coleta básica de info do dispositivo (existente)
# ---------------------------------------------------------------------------

async def _get_info_async(host: str, community: str, port: int, timeout: int, target: str) -> dict:
    from pysnmp.hlapi.asyncio import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity

    result = {"target": target}
    snmp_engine = SnmpEngine()
    auth = CommunityData(community, mpModel=1)
    transport = UdpTransportTarget((host, port), timeout=timeout)

    for name, oid in _BASIC_OIDS.items():
        err, err_status, err_idx, var_binds = await getCmd(
            snmp_engine, auth, transport, ContextData(), ObjectType(ObjectIdentity(oid)),
        )
        if err:
            result["error"] = f"{str(err)} (destino: {target}, community: {community})"
            return result
        if err_status:
            result["error"] = f"{err_status.prettyPrint()} (destino: {target})"
            return result
        for vb in var_binds:
            result[name] = str(vb[1])

    if "sysUpTime" in result:
        result["sysUpTime"] = _parse_uptime(result["sysUpTime"])
    return result


def _parse_uptime(timeticks: str) -> str:
    try:
        ticks = int(timeticks)
        secs = ticks // 100
        days, secs = divmod(secs, 86400)
        h, secs = divmod(secs, 3600)
        m, s = divmod(secs, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if h or parts:
            parts.append(f"{h}h")
        if m or parts:
            parts.append(f"{m}m")
        parts.append(f"{s}s")
        return " ".join(parts)
    except (ValueError, TypeError):
        return timeticks
