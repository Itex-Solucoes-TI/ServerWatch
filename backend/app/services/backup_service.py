from sqlmodel import Session, select
from app.models.company import Company
from app.models.company_settings import CompanySettings
from app.models.server import Server
from app.models.router import Router
from app.models.network_interface import NetworkInterface
from app.models.network_link import NetworkLink
from app.models.node_position import NodePosition
from app.models.health_check import HealthCheck
from app.models.notification import NotificationChannel, AlertRule
from app.models.user import User, UserCompanyRole


def _dict_exclude(obj, *keys):
    d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_") and k not in keys}
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in d.items() if v is not None}


def export_company_backup(session: Session, company_id: int) -> dict:
    company = session.get(Company, company_id)
    if not company or not company.active:
        raise ValueError("Empresa não encontrada")

    settings = session.exec(select(CompanySettings).where(CompanySettings.company_id == company_id)).first()
    servers = session.exec(select(Server).where(Server.company_id == company_id, Server.active == True)).all()
    routers = session.exec(select(Router).where(Router.company_id == company_id, Router.active == True)).all()

    server_ids = [s.id for s in servers]
    router_ids = [r.id for r in routers]

    interfaces = []
    if server_ids:
        for ni in session.exec(select(NetworkInterface).where(NetworkInterface.server_id.in_(server_ids))).all():
            interfaces.append({"server_id": ni.server_id, **{k: v for k, v in ni.__dict__.items() if not k.startswith("_") and k not in ("id", "server_id", "router_id")}, "router_id": None})
    if router_ids:
        for ni in session.exec(select(NetworkInterface).where(NetworkInterface.router_id.in_(router_ids))).all():
            interfaces.append({"router_id": ni.router_id, **{k: v for k, v in ni.__dict__.items() if not k.startswith("_") and k not in ("id", "server_id", "router_id")}, "server_id": None})

    links = session.exec(select(NetworkLink).where(NetworkLink.company_id == company_id, NetworkLink.active == True)).all()
    positions = session.exec(select(NodePosition).where(NodePosition.company_id == company_id)).all()
    checks = session.exec(select(HealthCheck).where(HealthCheck.company_id == company_id)).all()
    channels = session.exec(select(NotificationChannel).where(NotificationChannel.company_id == company_id)).all()
    rules = session.exec(select(AlertRule).where(AlertRule.company_id == company_id)).all()
    roles = session.exec(select(UserCompanyRole).where(UserCompanyRole.company_id == company_id)).all()
    user_ids = [r.user_id for r in roles]
    users_with_roles = []
    if user_ids:
        for r in roles:
            u = session.get(User, r.user_id)
            if u and u.active:
                users_with_roles.append(_dict_exclude(u, "id", "created_at") | {"_id": u.id, "role": r.role})

    backup = {
        "version": 1,
        "company": {"name": company.name, "slug": company.slug},
        "company_settings": _dict_exclude(settings, "id", "company_id") if settings else {},
        "servers": [_dict_exclude(s, "id", "company_id", "created_at") | {"_id": s.id} for s in servers],
        "routers": [_dict_exclude(r, "id", "company_id") | {"_id": r.id} for r in routers],
        "network_interfaces": interfaces,
        "network_links": [
            {"source_server_id": l.source_server_id, "source_router_id": l.source_router_id, "target_server_id": l.target_server_id, "target_router_id": l.target_router_id, "name": l.name, "link_type": l.link_type, "bandwidth_mbps": l.bandwidth_mbps}
            for l in links
        ],
        "node_positions": [{"node_type": p.node_type, "node_id": p.node_id, "position_x": p.position_x, "position_y": p.position_y} for p in positions],
        "health_checks": [_dict_exclude(c, "id", "company_id", "last_checked_at") | {"_id": c.id, "last_checked_at": None} for c in checks],
        "notification_channels": [_dict_exclude(ch, "id", "company_id", "created_at") | {"_id": ch.id} for ch in channels],
        "alert_rules": [_dict_exclude(r, "id", "company_id", "last_notified_at", "consecutive_failures") | {"last_notified_at": None, "consecutive_failures": 0} for r in rules],
        "users": users_with_roles,
    }
    return backup


def import_company_backup(session: Session, company_id: int, data: dict, replace: bool = False):
    company = session.get(Company, company_id)
    if not company or not company.active:
        raise ValueError("Empresa não encontrada")

    if replace:
        _clear_company_data(session, company_id)

    sid_map = {}
    rid_map = {}
    cid_map = {}
    chid_map = {}

    for s in data.get("servers", []):
        old_id = s.pop("_id", None)
        fields = {k: v for k, v in s.items() if k != "_id"}
        server = Server(company_id=company_id, **fields)
        session.add(server)
        session.flush()
        if old_id is not None:
            sid_map[old_id] = server.id

    for r in data.get("routers", []):
        old_id = r.pop("_id", None)
        fields = {k: v for k, v in r.items() if k != "_id"}
        router = Router(company_id=company_id, **fields)
        session.add(router)
        session.flush()
        if old_id is not None:
            rid_map[old_id] = router.id

    for ni in data.get("network_interfaces", []):
        server_id = ni.get("server_id")
        router_id = ni.get("router_id")
        if server_id is not None:
            server_id = sid_map.get(server_id, server_id)
        if router_id is not None:
            router_id = rid_map.get(router_id, router_id)
        fields = {k: v for k, v in ni.items() if k not in ("id", "server_id", "router_id") and v is not None}
        session.add(NetworkInterface(server_id=server_id, router_id=router_id, **fields))

    for lnk in data.get("network_links", []):
        src_s = sid_map.get(lnk.get("source_server_id"), lnk.get("source_server_id"))
        src_r = rid_map.get(lnk.get("source_router_id"), lnk.get("source_router_id"))
        tgt_s = sid_map.get(lnk.get("target_server_id"), lnk.get("target_server_id"))
        tgt_r = rid_map.get(lnk.get("target_router_id"), lnk.get("target_router_id"))
        session.add(NetworkLink(company_id=company_id, source_server_id=src_s, source_router_id=src_r, target_server_id=tgt_s, target_router_id=tgt_r, name=lnk.get("name"), link_type=lnk.get("link_type", "LAN"), bandwidth_mbps=lnk.get("bandwidth_mbps")))

    for chk in data.get("health_checks", []):
        old_id = chk.pop("_id", None)
        server_id = chk.get("server_id")
        router_id = chk.get("router_id")
        if server_id is not None:
            server_id = sid_map.get(server_id, server_id)
        if router_id is not None:
            router_id = rid_map.get(router_id, router_id)
        fields = {k: v for k, v in chk.items() if k not in ("id", "company_id", "_id", "server_id", "router_id")}
        check = HealthCheck(company_id=company_id, server_id=server_id, router_id=router_id, **fields)
        session.add(check)
        session.flush()
        if old_id is not None:
            cid_map[old_id] = check.id

    for ch in data.get("notification_channels", []):
        old_id = ch.pop("_id", None)
        fields = {k: v for k, v in ch.items() if k != "_id"}
        channel = NotificationChannel(company_id=company_id, **fields)
        session.add(channel)
        session.flush()
        if old_id is not None:
            chid_map[old_id] = channel.id

    for rule in data.get("alert_rules", []):
        check_id = cid_map.get(rule.get("check_id"), rule.get("check_id"))
        channel_id = chid_map.get(rule.get("channel_id"), rule.get("channel_id"))
        if check_id and channel_id:
            session.add(AlertRule(company_id=company_id, check_id=check_id, channel_id=channel_id, fail_threshold=rule.get("fail_threshold", 3), active=rule.get("active", True)))

    for pos in data.get("node_positions", []):
        node_type = pos.get("node_type")
        node_id = pos.get("node_id")
        if node_type == "SERVER":
            node_id = sid_map.get(node_id, node_id)
        elif node_type == "ROUTER":
            node_id = rid_map.get(node_id, node_id)
        if node_id is not None:
            session.add(NodePosition(company_id=company_id, node_type=node_type, node_id=node_id, position_x=pos.get("position_x", 0), position_y=pos.get("position_y", 0)))

    for u in data.get("users", []):
        old_id = u.pop("_id", None)
        role = u.pop("role", "VIEWER")
        existing = session.exec(select(User).where(User.email == u.get("email"))).first()
        if existing:
            user_id = existing.id
        else:
            fields = {k: v for k, v in u.items() if k in ("name", "email", "password_hash", "is_superadmin", "active")}
            new_user = User(**fields)
            session.add(new_user)
            session.flush()
            user_id = new_user.id
        existing_role = session.exec(select(UserCompanyRole).where(UserCompanyRole.company_id == company_id, UserCompanyRole.user_id == user_id)).first()
        if not existing_role:
            session.add(UserCompanyRole(company_id=company_id, user_id=user_id, role=role))

    settings_data = data.get("company_settings", {})
    if settings_data:
        s = session.exec(select(CompanySettings).where(CompanySettings.company_id == company_id)).first()
        if not s:
            s = CompanySettings(company_id=company_id)
            session.add(s)
            session.flush()
        for k in ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_from", "smtp_tls", "zapi_instance_id", "zapi_token", "zapi_client_token"]:
            if k in settings_data and settings_data[k] is not None:
                setattr(s, k, settings_data[k])

    session.commit()


def _clear_company_data(session: Session, company_id: int):
    from app.models.health_check import CheckResult
    for r in session.exec(select(AlertRule).where(AlertRule.company_id == company_id)).all():
        session.delete(r)
    for c in session.exec(select(HealthCheck).where(HealthCheck.company_id == company_id)).all():
        for cr in session.exec(select(CheckResult).where(CheckResult.check_id == c.id)).all():
            session.delete(cr)
        session.delete(c)
    for ch in session.exec(select(NotificationChannel).where(NotificationChannel.company_id == company_id)).all():
        session.delete(ch)
    for lnk in session.exec(select(NetworkLink).where(NetworkLink.company_id == company_id)).all():
        session.delete(lnk)
    for pos in session.exec(select(NodePosition).where(NodePosition.company_id == company_id)).all():
        session.delete(pos)
    for r in session.exec(select(UserCompanyRole).where(UserCompanyRole.company_id == company_id)).all():
        session.delete(r)
    for s in session.exec(select(Server).where(Server.company_id == company_id)).all():
        for ni in session.exec(select(NetworkInterface).where(NetworkInterface.server_id == s.id)).all():
            session.delete(ni)
        s.active = False
        session.add(s)
    for r in session.exec(select(Router).where(Router.company_id == company_id)).all():
        for ni in session.exec(select(NetworkInterface).where(NetworkInterface.router_id == r.id)).all():
            session.delete(ni)
        r.active = False
        session.add(r)
    session.flush()
