from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.deps import get_session, get_company_id, require_role
from app.models.router import Router
from app.models.network_interface import NetworkInterface
from app.schemas.router import RouterCreate, RouterUpdate, RouterRead
from app.schemas.server import NetworkInterfaceCreate
from app.services.audit_service import log
from app.services.snmp_service import get_info as snmp_get_info

router = APIRouter(prefix="/routers", tags=["routers"])


@router.get("", response_model=list[RouterRead])
def list_routers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    items = session.exec(select(Router).where(Router.company_id == company_id, Router.active == True).offset(skip).limit(limit)).all()
    return items


@router.post("", response_model=RouterRead)
def create_router(
    data: RouterCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    payload = data.model_dump(exclude={"interfaces", "create_ping_check"})
    r = Router(company_id=company_id, **payload)
    session.add(r)
    log(session, user.id, "CREATE", company_id, "ROUTER", None)
    session.commit()
    session.refresh(r)

    for i in data.interfaces or []:
        ni = NetworkInterface(router_id=r.id, **i.model_dump())
        session.add(ni)

    if data.create_ping_check:
        ping_target = _ping_target_from_router(r.id, session)
        if ping_target:
            from app.models.health_check import HealthCheck
            hc = HealthCheck(
                company_id=company_id,
                router_id=r.id,
                name=f"Ping {r.name}",
                check_type="PING",
                target=ping_target,
                interval_sec=60,
                timeout_sec=10,
                active=True,
            )
            session.add(hc)

    if data.interfaces or data.create_ping_check:
        session.commit()
        session.refresh(r)
    return r


def _ping_target_from_router(router_id: int, session: Session) -> str | None:
    """Retorna IP preferido para ping: is_primary primeiro."""
    return _snmp_host_from_router(router_id, None, session)


def _snmp_host_from_router(router_id: int, interface_id: int | None, session: Session) -> str | None:
    """Retorna IP para SNMP/ping. Se interface_id, usa essa; senão is_primary primeiro."""
    if interface_id:
        ni = session.get(NetworkInterface, interface_id)
        if ni and ni.router_id == router_id and (ni.ip_address or "").strip():
            return (ni.ip_address or "").strip().split("/")[0].split(" ")[0]
        return None
    interfaces = list(session.exec(select(NetworkInterface).where(NetworkInterface.router_id == router_id).order_by(NetworkInterface.is_primary.desc())))
    for ni in interfaces:
        ip = (ni.ip_address or "").strip().split("/")[0].split(" ")[0]
        if ip:
            return ip
    return None


@router.get("/{id}", response_model=RouterRead)
def get_router(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    return r


@router.put("/{id}", response_model=RouterRead)
def update_router(
    id: int,
    data: RouterUpdate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    log(session, user.id, "UPDATE", company_id, "ROUTER", id)
    session.commit()
    session.refresh(r)
    return r


@router.delete("/{id}")
def delete_router(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    r.active = False
    log(session, user.id, "DELETE", company_id, "ROUTER", id)
    session.commit()
    return {"ok": True}


@router.get("/{id}/interfaces")
def list_interfaces(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    items = session.exec(select(NetworkInterface).where(NetworkInterface.router_id == id)).all()
    return items


@router.post("/{id}/interfaces")
def add_interface(
    id: int,
    data: NetworkInterfaceCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    ni = NetworkInterface(router_id=id, **data.model_dump())
    session.add(ni)
    session.commit()
    session.refresh(ni)
    return ni


@router.put("/{id}/interfaces/{interface_id}")
def update_interface(
    id: int,
    interface_id: int,
    data: NetworkInterfaceCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    ni = session.get(NetworkInterface, interface_id)
    if not ni or ni.router_id != id:
        raise HTTPException(404, "Não encontrado")
    for k, v in data.model_dump().items():
        setattr(ni, k, v)
    session.add(ni)
    session.commit()
    session.refresh(ni)
    return ni


@router.get("/{id}/snmp-discover")
def snmp_discover(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    """Walk SNMP e retorna todos os OIDs respondidos com nome e categoria identificados."""
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    if not r.snmp_enabled:
        raise HTTPException(400, "Habilite SNMP e salve antes de descobrir.")
    host = _snmp_host_from_router(id, None, session)
    if not host:
        raise HTTPException(400, "Nenhum IP configurado.")
    community = (r.snmp_community or "public").strip() or "public"
    from app.services.snmp_discovery import discover
    return discover(host, community, r.snmp_port or 161)


@router.get("/{id}/snmp-info")
def get_router_snmp_info(
    id: int,
    interface_id: int | None = Query(None, description="ID da interface para usar (opcional; usa primeira LAN por padrão)"),
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    if not r.snmp_enabled:
        raise HTTPException(400, "Habilite SNMP no cadastro do roteador e salve antes de consultar.")
    community = (r.snmp_community or "").strip() or "public"
    host = _snmp_host_from_router(id, interface_id, session)
    if not host:
        raise HTTPException(400, "Nenhum IP configurado. Adicione uma interface com IP (ex: 192.168.0.1) e marque LAN se for a principal.")
    return snmp_get_info(host, community, r.snmp_port or 161)


# ---------------------------------------------------------------------------
# SNMP Monitors
# ---------------------------------------------------------------------------

@router.get("/{id}/snmp-monitors")
def list_snmp_monitors(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.snmp_monitor import SnmpMonitor
    return session.exec(select(SnmpMonitor).where(SnmpMonitor.router_id == id)).all()


@router.post("/{id}/snmp-monitors")
def create_snmp_monitor(
    id: int,
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.snmp_monitor import SnmpMonitor
    valid = {"metric_type", "custom_oid", "interface_filter", "interval_sec", "threshold_warn", "threshold_unit", "active"}
    m = SnmpMonitor(router_id=id, **{k: v for k, v in data.items() if k in valid})
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


@router.put("/{id}/snmp-monitors/{mid}")
def update_snmp_monitor(
    id: int,
    mid: int,
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.snmp_monitor import SnmpMonitor
    m = session.get(SnmpMonitor, mid)
    if not m or m.router_id != id:
        raise HTTPException(404)
    valid = {"custom_oid", "interface_filter", "interval_sec", "threshold_warn", "threshold_unit", "active"}
    for k, v in data.items():
        if k in valid:
            setattr(m, k, v)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


@router.delete("/{id}/snmp-monitors/{mid}")
def delete_snmp_monitor(
    id: int,
    mid: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.snmp_monitor import SnmpMonitor
    m = session.get(SnmpMonitor, mid)
    if not m or m.router_id != id:
        raise HTTPException(404)
    session.delete(m)
    session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# SNMP Metrics
# ---------------------------------------------------------------------------

@router.get("/{id}/snmp-latest")
def snmp_latest(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    """Última leitura de cada tipo de métrica para este roteador."""
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.snmp_metric import SnmpMetric
    metrics = session.exec(select(SnmpMetric).where(SnmpMetric.router_id == id)).all()
    latest: dict[str, dict] = {}
    for m in metrics:
        key = f"{m.metric_type}:{m.interface_name or ''}"
        if key not in latest or m.collected_at > latest[key]["collected_at"]:
            latest[key] = {"metric_type": m.metric_type, "interface_name": m.interface_name, "value": m.value, "unit": m.unit, "collected_at": m.collected_at}
    return list(latest.values())


@router.get("/{id}/snmp-metrics")
def snmp_metrics_history(
    id: int,
    metric_type: str = Query(...),
    interface_name: str | None = Query(None),
    hours: int = Query(24, ge=1, le=168),
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    """Histórico de métricas SNMP para gráficos."""
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.snmp_metric import SnmpMetric
    from datetime import datetime, timedelta
    since = datetime.utcnow() - timedelta(hours=hours)
    q = select(SnmpMetric).where(
        SnmpMetric.router_id == id,
        SnmpMetric.metric_type == metric_type,
        SnmpMetric.collected_at >= since,
    )
    if interface_name:
        q = q.where(SnmpMetric.interface_name == interface_name)
    q = q.order_by(SnmpMetric.collected_at.asc())
    return session.exec(q).all()


@router.post("/{id}/snmp-collect")
def snmp_collect_now(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    """Força coleta SNMP imediata para este roteador."""
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    if not r.snmp_enabled:
        raise HTTPException(400, "SNMP não habilitado")
    from app.models.snmp_monitor import SnmpMonitor
    from app.services.snmp_service import _collect_monitor, _get_router_host
    monitors = session.exec(select(SnmpMonitor).where(SnmpMonitor.router_id == id, SnmpMonitor.active == True)).all()
    host = _get_router_host(id, session)
    if not host:
        raise HTTPException(400, "Nenhum IP configurado")
    community = (r.snmp_community or "public").strip() or "public"
    for m in monitors:
        _collect_monitor(m, host, community, r.snmp_port or 161, session)
    return {"ok": True, "collected": len(monitors)}


@router.post("/{id}/clone")
def clone_router(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    """Clona um roteador: dados, interfaces e monitores SNMP. Nome recebe sufixo ' (cópia)'."""
    src = session.get(Router, id)
    if not src or src.company_id != company_id:
        raise HTTPException(404)

    from app.models.network_interface import NetworkInterface
    from app.models.snmp_monitor import SnmpMonitor

    # Copia o roteador
    new_router = Router(
        company_id=src.company_id,
        name=src.name + " (cópia)",
        brand=src.brand,
        model=src.model,
        location=src.location,
        device_type=src.device_type,
        has_vpn=src.has_vpn,
        has_external_ip=src.has_external_ip,
        gateway=src.gateway,
        dns_primary=src.dns_primary,
        dns_secondary=src.dns_secondary,
        wifi_ssid=src.wifi_ssid,
        wifi_band=src.wifi_band,
        wifi_channel=src.wifi_channel,
        snmp_enabled=src.snmp_enabled,
        snmp_community=src.snmp_community,
        snmp_port=src.snmp_port,
    )
    session.add(new_router)
    session.commit()
    session.refresh(new_router)

    # Copia interfaces
    for ni in session.exec(select(NetworkInterface).where(NetworkInterface.router_id == id)).all():
        session.add(NetworkInterface(
            router_id=new_router.id,
            ip_address=ni.ip_address,
            subnet_mask=ni.subnet_mask,
            interface_name=ni.interface_name,
            is_external=ni.is_external,
            is_primary=ni.is_primary,
            is_vpn=ni.is_vpn,
        ))

    # Copia monitores SNMP
    for m in session.exec(select(SnmpMonitor).where(SnmpMonitor.router_id == id)).all():
        session.add(SnmpMonitor(
            router_id=new_router.id,
            metric_type=m.metric_type,
            custom_oid=m.custom_oid,
            interface_filter=m.interface_filter,
            interval_sec=m.interval_sec,
            threshold_warn=m.threshold_warn,
            active=m.active,
        ))

    # Copia redes WiFi
    from app.models.wifi_network import WifiNetwork
    for wn in session.exec(select(WifiNetwork).where(WifiNetwork.router_id == id)).all():
        session.add(WifiNetwork(
            router_id=new_router.id, ssid=wn.ssid, band=wn.band,
            channel=wn.channel, password=wn.password, vlan=wn.vlan,
            notes=wn.notes, active=wn.active,
        ))

    session.commit()
    return {"ok": True, "new_router_id": new_router.id, "name": new_router.name}


@router.post("/{id}/snmp-copy-to/{target_id}")
def snmp_copy_monitors(
    id: int,
    target_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    """Copia todos os monitores SNMP do roteador `id` para `target_id`."""
    src = session.get(Router, id)
    dst = session.get(Router, target_id)
    if not src or src.company_id != company_id:
        raise HTTPException(404, "Roteador origem não encontrado")
    if not dst or dst.company_id != company_id:
        raise HTTPException(404, "Roteador destino não encontrado")

    from app.models.snmp_monitor import SnmpMonitor

    monitors = session.exec(select(SnmpMonitor).where(SnmpMonitor.router_id == id)).all()
    if not monitors:
        raise HTTPException(400, "Nenhum monitor configurado no roteador origem")

    # OIDs existentes no destino para evitar duplicatas
    existing_oids = {
        (m.metric_type, m.custom_oid or "", m.interface_filter or "")
        for m in session.exec(select(SnmpMonitor).where(SnmpMonitor.router_id == target_id)).all()
    }

    copied = 0
    for m in monitors:
        key = (m.metric_type, m.custom_oid or "", m.interface_filter or "")
        if key in existing_oids:
            continue
        session.add(SnmpMonitor(
            router_id=target_id,
            metric_type=m.metric_type,
            custom_oid=m.custom_oid,
            interface_filter=m.interface_filter,
            interval_sec=m.interval_sec,
            threshold_warn=m.threshold_warn,
            active=m.active,
        ))
        copied += 1

    session.commit()
    return {"ok": True, "copied": copied, "skipped": len(monitors) - copied}


@router.delete("/{id}/interfaces/{interface_id}")
def delete_interface(
    id: int,
    interface_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404, "Não encontrado")
    ni = session.get(NetworkInterface, interface_id)
    if not ni or ni.router_id != id:
        raise HTTPException(404, "Não encontrado")
    session.delete(ni)
    session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# WiFi Networks
# ---------------------------------------------------------------------------

@router.get("/{id}/wifi-networks")
def list_wifi_networks(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.wifi_network import WifiNetwork
    return session.exec(select(WifiNetwork).where(WifiNetwork.router_id == id).order_by(WifiNetwork.id)).all()


@router.post("/{id}/wifi-networks")
def create_wifi_network(
    id: int,
    payload: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.wifi_network import WifiNetwork
    wn = WifiNetwork(router_id=id, **{k: v for k, v in payload.items() if k != 'router_id'})
    session.add(wn)
    session.commit()
    session.refresh(wn)
    return wn


@router.put("/{id}/wifi-networks/{wid}")
def update_wifi_network(
    id: int,
    wid: int,
    payload: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.wifi_network import WifiNetwork
    wn = session.get(WifiNetwork, wid)
    if not wn or wn.router_id != id:
        raise HTTPException(404)
    for k, v in payload.items():
        if k not in ('id', 'router_id'):
            setattr(wn, k, v)
    session.add(wn)
    session.commit()
    session.refresh(wn)
    return wn


@router.delete("/{id}/wifi-networks/{wid}")
def delete_wifi_network(
    id: int,
    wid: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    r = session.get(Router, id)
    if not r or r.company_id != company_id:
        raise HTTPException(404)
    from app.models.wifi_network import WifiNetwork
    wn = session.get(WifiNetwork, wid)
    if not wn or wn.router_id != id:
        raise HTTPException(404)
    session.delete(wn)
    session.commit()
    return {"ok": True}


@router.post("/{id}/wifi-networks/copy-to/{target_id}")
def copy_wifi_networks(
    id: int,
    target_id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR")),
    session: Session = Depends(get_session),
):
    """Copia redes WiFi do roteador origem para o destino, ignorando SSIDs já existentes."""
    src = session.get(Router, id)
    dst = session.get(Router, target_id)
    if not src or src.company_id != company_id:
        raise HTTPException(404, "Origem não encontrada")
    if not dst or dst.company_id != company_id:
        raise HTTPException(404, "Destino não encontrado")
    from app.models.wifi_network import WifiNetwork
    networks = session.exec(select(WifiNetwork).where(WifiNetwork.router_id == id)).all()
    if not networks:
        raise HTTPException(400, "Nenhuma rede WiFi configurada na origem")
    existing_ssids = {
        wn.ssid for wn in session.exec(select(WifiNetwork).where(WifiNetwork.router_id == target_id)).all()
    }
    copied = 0
    for wn in networks:
        if wn.ssid in existing_ssids:
            continue
        session.add(WifiNetwork(
            router_id=target_id, ssid=wn.ssid, band=wn.band,
            channel=wn.channel, password=wn.password, vlan=wn.vlan,
            notes=wn.notes, active=wn.active,
        ))
        copied += 1
    session.commit()
    return {"ok": True, "copied": copied, "skipped": len(networks) - copied}
