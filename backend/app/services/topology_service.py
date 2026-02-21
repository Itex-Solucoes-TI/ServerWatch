import ipaddress
from sqlalchemy import or_
from sqlmodel import Session, select
from app.models.server import Server
from app.models.router import Router
from app.models.network_interface import NetworkInterface
from app.models.network_link import NetworkLink
from app.models.node_position import NodePosition
from app.models.docker_snapshot import DockerSnapshot
from app.models.generic_device import GenericDevice


def _infer_cidr(ip_address: str) -> str | None:
    """RFC 1918: infer /24 para IPs privados quando máscara não informada."""
    try:
        ip = ipaddress.ip_address(ip_address.strip())
        if ip.is_private:
            return "/24"
    except (ValueError, ipaddress.AddressValueError):
        pass
    return None


def _parse_subnet(ip_address: str, subnet_mask: str | None) -> str | None:
    if not ip_address:
        return None
    try:
        ip_str = ip_address.strip()
        if not ip_str:
            return None
        mask = (subnet_mask or "").strip()
        if not mask:
            cidr = _infer_cidr(ip_str)
            if not cidr:
                return None
        elif mask.startswith("/"):
            cidr = mask if len(mask) > 1 else None
        elif "." in mask:
            cidr = f"/{sum(bin(int(x)).count('1') for x in mask.split('.'))}"
        elif mask.isdigit():
            cidr = f"/{int(mask)}"
        else:
            cidr = f"/{mask}"
        if not cidr:
            return None
        iface = ipaddress.ip_interface(f"{ip_str}{cidr}")
        return str(iface.network)
    except (ValueError, ipaddress.AddressValueError):
        return None


def _get_node_id(server_id=None, router_id=None, generic_id=None) -> str | None:
    if server_id:
        return f"S-{server_id}"
    if router_id:
        return f"R-{router_id}"
    if generic_id:
        return f"G-{generic_id}"
    return None


def get_graph(session: Session, company_id: int):
    servers = session.exec(select(Server).where(Server.company_id == company_id, Server.active == True)).all()
    routers = session.exec(select(Router).where(Router.company_id == company_id, Router.active == True)).all()
    generics = session.exec(select(GenericDevice).where(GenericDevice.company_id == company_id, GenericDevice.active == True)).all()
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
                "device_type": "SERVER",
                "server": {"id": s.id, "name": s.name},
                "interfaces": [{"ip_address": iface.ip_address} for iface in interfaces],
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
            "data": {
                "label": r.name,
                "device_type": r.device_type,
                "router": {"id": r.id, "name": r.name, "has_vpn": r.has_vpn},
                "interfaces": [{"ip_address": iface.ip_address} for iface in interfaces],
            },
            "position": {"x": pos[0], "y": pos[1]},
        })

    for i, g in enumerate(generics):
        pos = pos_map.get(("GENERIC", g.id), (500 + (i % 3) * 200, 500 + (i // 3) * 150))
        nodes.append({
            "id": f"G-{g.id}",
            "type": "generic",
            "data": {
                "label": g.name,
                "device_type": g.device_type,
                "generic": {
                    "id": g.id,
                    "name": g.name,
                    "device_type": g.device_type,
                    "ip_address": g.ip_address,
                    "rtsp_port": g.rtsp_port,
                    "rtsp_channel": g.rtsp_channel,
                    "rtsp_subtype": g.rtsp_subtype,
                    "has_credentials": bool(g.rtsp_username),
                },
            },
            "position": {"x": pos[0], "y": pos[1]},
        })

    node_ids = {n["id"] for n in nodes}
    edges = []
    seen_edges = set()

    for link in links:
        src = _get_node_id(link.source_server_id, link.source_router_id, link.source_generic_id)
        tgt = _get_node_id(link.target_server_id, link.target_router_id, link.target_generic_id)
        if not src or not tgt:
            continue
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
            "data": {"label": "Internet", "device_type": "INTERNET"},
            "position": {"x": pos[0], "y": pos[1]},
        })
        node_ids.add("INTERNET")
    if has_vpn and "VPN" not in node_ids:
        pos = pos_map.get(("VPN", 0), (base_x, 20))
        nodes.append({
            "id": "VPN",
            "type": "router",
            "data": {"label": "VPN", "device_type": "VPN"},
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

    # Ligações LAN: apenas interfaces marcadas como LAN (is_primary) na mesma sub-rede
    lan_interfaces = [(i, _parse_subnet(i.ip_address, i.subnet_mask)) for i in all_interfaces if not i.is_external and i.is_primary]
    for i, (iface_a, net_a) in enumerate(lan_interfaces):
        if not net_a:
            continue
        nid_a = _get_node_id(iface_a.server_id, iface_a.router_id)
        for iface_b, net_b in lan_interfaces[i + 1 :]:
            if not net_b or net_a != net_b:
                continue
            nid_b = _get_node_id(iface_b.server_id, iface_b.router_id)
            if nid_a == nid_b:
                continue
            key = tuple(sorted([nid_a, nid_b]))
            if key not in seen_edges and nid_a in node_ids and nid_b in node_ids:
                seen_edges.add(key)
                edges.append({"id": f"e-auto-lan-{nid_a}-{nid_b}", "source": nid_a, "target": nid_b, "data": {"linkId": None, "linkType": "LAN", "auto": True}})

    # Auto-link câmeras/dispositivos genéricos ao switch/roteador na mesma subnet.
    # Regras:
    # - WIFI_AP é ignorado (câmeras ligam via cabo)
    # - Se houver 1 SWITCH na subnet → liga nele
    # - Se houver 2+ SWITCHes na mesma subnet → ambíguo, não liga automaticamente
    # - Se não houver SWITCH → tenta FIREWALL/ROUTER (único na subnet)
    # - Se houver 2+ ROUTERs na subnet sem SWITCH → ambíguo, não liga

    # Mapa: net -> lista de (nid, device_type)
    subnet_candidates: dict[str, list[tuple[str, str]]] = {}
    for iface in all_interfaces:
        if iface.is_external or iface.is_vpn:
            continue
        net = _parse_subnet(iface.ip_address, iface.subnet_mask)
        if not net:
            continue
        nid = _get_node_id(iface.server_id, iface.router_id)
        if not nid or nid not in node_ids:
            continue
        node = next((n for n in nodes if n["id"] == nid), None)
        if not node:
            continue
        dtype = node["data"].get("device_type", "OTHER")
        if dtype == "WIFI_AP":
            continue
        if net not in subnet_candidates:
            subnet_candidates[net] = []
        # Evitar duplicar o mesmo nó (router com múltiplas interfaces na mesma subnet)
        if not any(n == nid for n, _ in subnet_candidates[net]):
            subnet_candidates[net].append((nid, dtype))

    def _resolve_parent(candidates: list[tuple[str, str]]) -> str | None:
        """Retorna o nó pai único ou None se ambíguo."""
        switches = [nid for nid, dt in candidates if dt == "SWITCH"]
        if len(switches) == 1:
            return switches[0]
        if len(switches) > 1:
            return None  # ambíguo: 2+ switches, precisa ligação manual
        # Sem switch: tenta FIREWALL ou ROUTER único
        wired = [nid for nid, dt in candidates if dt in ("FIREWALL", "ROUTER")]
        if len(wired) == 1:
            return wired[0]
        return None  # ambíguo ou vazio

    for g in generics:
        if not g.ip_address:
            continue
        g_nid = f"G-{g.id}"
        if g_nid not in node_ids:
            continue
        for prefix in (24, 16):
            try:
                net = str(ipaddress.ip_interface(f"{g.ip_address.strip()}/{prefix}").network)
            except ValueError:
                continue
            candidates = subnet_candidates.get(net, [])
            parent_nid = _resolve_parent(candidates)
            if parent_nid:
                key = tuple(sorted([g_nid, parent_nid]))
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({
                        "id": f"e-auto-cam-{g_nid}",
                        "source": parent_nid,
                        "target": g_nid,
                        "data": {"linkId": None, "linkType": "LAN", "auto": True},
                    })
                break
            elif candidates:
                # Ambíguo: marca o nó para sinalizar no frontend
                node = next((n for n in nodes if n["id"] == g_nid), None)
                if node:
                    node["data"]["link_ambiguous"] = True
                break

    return {"nodes": nodes, "edges": edges}
