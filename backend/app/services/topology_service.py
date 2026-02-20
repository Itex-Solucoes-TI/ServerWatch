import ipaddress
from sqlalchemy import or_
from sqlmodel import Session, select
from app.models.server import Server
from app.models.router import Router
from app.models.network_interface import NetworkInterface
from app.models.network_link import NetworkLink
from app.models.node_position import NodePosition
from app.models.docker_snapshot import DockerSnapshot


def _parse_subnet(ip_address: str, subnet_mask: str | None) -> str | None:
    if not subnet_mask or not ip_address:
        return None
    try:
        mask = subnet_mask.strip()
        if mask.startswith("/"):
            cidr = mask
        elif "." in mask:
            cidr = f"/{sum(bin(int(x)).count('1') for x in mask.split('.'))}"
        else:
            cidr = f"/{int(mask)}" if mask.isdigit() else f"/{mask}"
        iface = ipaddress.ip_interface(f"{ip_address}{cidr}")
        return str(iface.network)
    except (ValueError, ipaddress.AddressValueError):
        return None


def _get_node_id(server_id: int | None, router_id: int | None) -> str:
    return f"S-{server_id}" if server_id else f"R-{router_id}"


def get_graph(session: Session, company_id: int):
    servers = session.exec(select(Server).where(Server.company_id == company_id, Server.active == True)).all()
    routers = session.exec(select(Router).where(Router.company_id == company_id, Router.active == True)).all()
    positions = session.exec(select(NodePosition).where(NodePosition.company_id == company_id)).all()
    pos_map = {(p.node_type, p.node_id): (p.position_x, p.position_y) for p in positions}
    links = session.exec(select(NetworkLink).where(NetworkLink.company_id == company_id, NetworkLink.active == True)).all()

    nodes = []
    for i, s in enumerate(servers):
        interfaces = session.exec(select(NetworkInterface).where(NetworkInterface.server_id == s.id)).all()
        containers = []
        if s.has_docker:
            snaps = session.exec(select(DockerSnapshot).where(DockerSnapshot.server_id == s.id)).all()
            containers = [{"name": c.name, "image": c.image, "status": c.status} for c in snaps]
        pos = pos_map.get(("SERVER", s.id), (150 + (i % 3) * 280, 80 + (i // 3) * 200))
        nodes.append({
            "id": f"S-{s.id}",
            "type": "server",
            "data": {
                "label": s.name,
                "server": {"id": s.id, "name": s.name},
                "interfaces": [{"ip_address": i.ip_address} for i in interfaces],
                "containers": containers,
            },
            "position": {"x": pos[0], "y": pos[1]},
        })
    for i, r in enumerate(routers):
        interfaces = session.exec(select(NetworkInterface).where(NetworkInterface.router_id == r.id)).all()
        pos = pos_map.get(("ROUTER", r.id), (150 + (i % 3) * 280, 320 + (i // 3) * 200))
        nodes.append({
            "id": f"R-{r.id}",
            "type": "router",
            "data": {"label": r.name, "router": {"id": r.id, "name": r.name, "has_vpn": r.has_vpn}, "interfaces": [{"ip_address": i.ip_address} for i in interfaces]},
            "position": {"x": pos[0], "y": pos[1]},
        })

    node_ids = {n["id"] for n in nodes}
    edges = []
    seen_edges = set()
    for link in links:
        src = _get_node_id(link.source_server_id, link.source_router_id)
        tgt = _get_node_id(link.target_server_id, link.target_router_id)
        key = tuple(sorted([src, tgt]))
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append({"id": f"e-{link.id}", "source": src, "target": tgt, "data": {"linkId": link.id, "linkType": link.link_type}})

    server_ids = [s.id for s in servers]
    router_ids = [r.id for r in routers]
    cond = []
    if server_ids:
        cond.append(NetworkInterface.server_id.in_(server_ids))
    if router_ids:
        cond.append(NetworkInterface.router_id.in_(router_ids))
    all_interfaces = list(session.exec(select(NetworkInterface).where(or_(*cond)))) if cond else []

    has_external = any(i.is_external for i in all_interfaces)
    has_vpn = any(i.is_vpn for i in all_interfaces)
    base_x = 400
    if has_external and "INTERNET" not in node_ids:
        pos = pos_map.get(("INTERNET", 0), (base_x, 500))
        nodes.append({
            "id": "INTERNET",
            "type": "router",
            "data": {"label": "Internet"},
            "position": {"x": pos[0], "y": pos[1]},
        })
        node_ids.add("INTERNET")
    if has_vpn and "VPN" not in node_ids:
        pos = pos_map.get(("VPN", 0), (base_x, 20))
        nodes.append({
            "id": "VPN",
            "type": "router",
            "data": {"label": "VPN"},
            "position": {"x": pos[0], "y": pos[1]},
        })
        node_ids.add("VPN")

    for i in all_interfaces:
        nid = _get_node_id(i.server_id, i.router_id)
        if not nid or nid not in node_ids:
            continue
        if i.is_external and has_external:
            key = tuple(sorted([nid, "INTERNET"]))
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append({"id": f"e-auto-inet-{nid}", "source": nid, "target": "INTERNET", "data": {"linkId": None, "linkType": "INTERNET", "auto": True}})
        if i.is_vpn and has_vpn:
            key = tuple(sorted([nid, "VPN"]))
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append({"id": f"e-auto-vpn-{nid}", "source": nid, "target": "VPN", "data": {"linkId": None, "linkType": "VPN", "auto": True}})

    private_interfaces = [(i, _parse_subnet(i.ip_address, i.subnet_mask)) for i in all_interfaces if not i.is_external and i.subnet_mask]
    for i, (iface_a, net_a) in enumerate(private_interfaces):
        if not net_a:
            continue
        nid_a = _get_node_id(iface_a.server_id, iface_a.router_id)
        for iface_b, net_b in private_interfaces[i + 1 :]:
            if not net_b or net_a != net_b:
                continue
            nid_b = _get_node_id(iface_b.server_id, iface_b.router_id)
            if nid_a == nid_b:
                continue
            key = tuple(sorted([nid_a, nid_b]))
            if key not in seen_edges and nid_a in node_ids and nid_b in node_ids:
                seen_edges.add(key)
                edges.append({"id": f"e-auto-lan-{nid_a}-{nid_b}", "source": nid_a, "target": nid_b, "data": {"linkId": None, "linkType": "LAN", "auto": True}})

    return {"nodes": nodes, "edges": edges}
