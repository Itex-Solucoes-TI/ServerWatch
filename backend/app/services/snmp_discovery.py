"""
Descoberta SNMP: faz WALK nas MIBs padrão e retorna o que o aparelho suporta,
com nome legível, valor e categoria identificada.
"""
import asyncio

# Mapa OID-prefixo -> (nome legível, categoria, dica de uso)
OID_MAP = {
    # === System ===
    "1.3.6.1.2.1.1.1.0":  ("sysDescr",        "Sistema",    "Descrição do sistema"),
    "1.3.6.1.2.1.1.3.0":  ("sysUpTime",        "Sistema",    "Tempo ligado"),
    "1.3.6.1.2.1.1.5.0":  ("sysName",          "Sistema",    "Nome do equipamento"),
    "1.3.6.1.2.1.1.4.0":  ("sysContact",       "Sistema",    "Contato"),
    "1.3.6.1.2.1.1.6.0":  ("sysLocation",      "Sistema",    "Localização"),
    # === Interfaces ===
    "1.3.6.1.2.1.2.2.1.2":  ("ifDescr",        "Interfaces", "Nome da interface"),
    "1.3.6.1.2.1.2.2.1.8":  ("ifOperStatus",   "Interfaces", "Status (1=up, 2=down)"),
    "1.3.6.1.2.1.2.2.1.10": ("ifInOctets",     "Tráfego",    "Bytes recebidos (IN) — use para TRAFFIC_IN"),
    "1.3.6.1.2.1.2.2.1.16": ("ifOutOctets",    "Tráfego",    "Bytes enviados (OUT) — use para TRAFFIC_OUT"),
    "1.3.6.1.2.1.2.2.1.11": ("ifInUcastPkts",  "Tráfego",    "Pacotes unicast recebidos"),
    "1.3.6.1.2.1.2.2.1.13": ("ifInDiscards",   "Tráfego",    "Pacotes descartados IN"),
    "1.3.6.1.2.1.2.2.1.14": ("ifInErrors",     "Tráfego",    "Erros IN"),
    "1.3.6.1.2.1.2.2.1.19": ("ifOutDiscards",  "Tráfego",    "Pacotes descartados OUT"),
    "1.3.6.1.2.1.2.2.1.20": ("ifOutErrors",    "Tráfego",    "Erros OUT"),
    # === HOST-RESOURCES CPU ===
    "1.3.6.1.2.1.25.3.3.1.2": ("hrProcessorLoad", "CPU",     "Carga % por núcleo — use para CPU"),
    # === HOST-RESOURCES Memory/Storage ===
    "1.3.6.1.2.1.25.2.3.1.3":  ("hrStorageDescr",      "Memória/Disco", "Descrição do storage"),
    "1.3.6.1.2.1.25.2.3.1.4":  ("hrStorageAllocUnits", "Memória/Disco", "Tamanho da unidade de alocação (bytes)"),
    "1.3.6.1.2.1.25.2.3.1.5":  ("hrStorageSize",       "Memória/Disco", "Tamanho total (em unidades)"),
    "1.3.6.1.2.1.25.2.3.1.6":  ("hrStorageUsed",       "Memória/Disco", "Usado (em unidades) — use para MEMORY"),
    # === MikroTik específico ===
    "1.3.6.1.4.1.14988.1.1.1.2.1.1": ("mtxrWlStatIndex",   "WiFi (MikroTik)", "Índice cliente wireless — use para WIFI_CLIENTS"),
    "1.3.6.1.4.1.14988.1.1.1.2.1.3": ("mtxrWlStatMacAddr", "WiFi (MikroTik)", "MAC dos clientes wireless"),
    "1.3.6.1.4.1.14988.1.1.1.2.1.2": ("mtxrWlStatTxRate",  "WiFi (MikroTik)", "Taxa de TX por cliente"),
    "1.3.6.1.4.1.14988.1.1.3.14.0":  ("mtxrCPUFrequency",  "CPU (MikroTik)",  "Frequência da CPU"),
    "1.3.6.1.4.1.14988.1.1.3.11.0":  ("mtxrCPULoad",       "CPU (MikroTik)",  "Carga da CPU % — use para CPU"),
    "1.3.6.1.4.1.14988.1.1.3.12.0":  ("mtxrCPUCount",      "CPU (MikroTik)",  "Núcleos de CPU"),
    "1.3.6.1.4.1.14988.1.1.3.15.0":  ("mtxrMemTotal",      "Memória (MikroTik)", "Total de memória RAM"),
    "1.3.6.1.4.1.14988.1.1.3.16.0":  ("mtxrMemAvailable",  "Memória (MikroTik)", "Memória disponível — use para MEMORY"),
    "1.3.6.1.4.1.14988.1.1.7.5.0":   ("mtxrBoardTemp",     "Hardware (MikroTik)", "Temperatura da placa °C"),
    "1.3.6.1.4.1.14988.1.1.7.6.0":   ("mtxrBoardTemp2",    "Hardware (MikroTik)", "Temperatura do processador °C"),
    # === Ubiquiti ===
    "1.3.6.1.4.1.41112.1.4.5.1.5":   ("ubntCpuLoad",       "CPU (Ubiquiti)",  "Carga CPU — use para CPU"),
    "1.3.6.1.4.1.41112.1.4.1.1.0":   ("ubntWlStaCnt",      "WiFi (Ubiquiti)", "Clientes WiFi conectados — use para WIFI_CLIENTS"),
}

# Prefixos para WALK (procura entradas em subtree inteira)
WALK_SUBTREES = [
    "1.3.6.1.2.1.1",        # System
    "1.3.6.1.2.1.2.2.1",    # Interfaces
    "1.3.6.1.2.1.25.3.3",   # HOST-RESOURCES CPU
    "1.3.6.1.2.1.25.2.3",   # HOST-RESOURCES Storage
    "1.3.6.1.4.1.14988.1.1.1.2",  # MikroTik WiFi clients
    "1.3.6.1.4.1.14988.1.1.3",    # MikroTik system stats
    "1.3.6.1.4.1.14988.1.1.7",    # MikroTik hardware
    "1.3.6.1.4.1.41112.1.4",      # Ubiquiti
]


def discover(host: str, community: str = "public", port: int = 161, timeout: int = 8) -> dict:
    """Descobre OIDs respondidos pelo aparelho e retorna lista organizada por categoria."""
    host = _clean(host)
    if not host:
        return {"error": "Host inválido", "results": []}
    try:
        return asyncio.run(_discover(host, community, port, timeout))
    except Exception as e:
        return {"error": str(e)[:200], "results": []}


async def _discover(host: str, community: str, port: int, timeout: int) -> dict:
    from pysnmp.hlapi.asyncio import nextCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity

    engine = SnmpEngine()
    auth = CommunityData(community, mpModel=1)
    transport = UdpTransportTarget((host, port), timeout=timeout, retries=1)
    ctx = ContextData()

    raw: list[dict] = []
    seen_oids = set()

    for subtree in WALK_SUBTREES:
        oid_obj = ObjectType(ObjectIdentity(subtree))
        steps = 0
        while steps < 200:  # limite de segurança por subtree
            steps += 1
            try:
                err, err_status, _, var_binds = await nextCmd(engine, auth, transport, ctx, oid_obj)
            except Exception:
                break
            if err or err_status or not var_binds or not var_binds[0]:
                break
            obj_type = var_binds[0][0]  # var_binds[row][col] -> ObjectType
            oid = obj_type[0]
            value = obj_type[1]
            oid_str = str(oid)
            if not oid_str.startswith(subtree):
                break
            if oid_str in seen_oids:
                break
            seen_oids.add(oid_str)

            val_str = str(value)
            # Ignora valores vazios ou muito longos (como MACAddresses brutas)
            if not val_str or val_str == "No Such Object currently exists at this OID" or val_str == "No Such Instance":
                oid_obj = ObjectType(ObjectIdentity(oid_str))
                continue

            # Tenta identificar pelo mapa
            info = _lookup(oid_str)
            raw.append({
                "oid": oid_str,
                "name": info["name"],
                "category": info["category"],
                "hint": info["hint"],
                "value": val_str[:200],
                "known": info["known"],
            })
            oid_obj = ObjectType(ObjectIdentity(oid_str))

    # Organiza por categoria
    categories: dict[str, list] = {}
    for r in raw:
        cat = r["category"]
        categories.setdefault(cat, []).append(r)

    return {
        "host": host,
        "community": community,
        "total": len(raw),
        "categories": categories,
        "results": raw,
    }


def _lookup(oid_str: str) -> dict:
    """Tenta casar o OID com o mapa de nomes conhecidos."""
    # Tenta match exato
    if oid_str in OID_MAP:
        name, cat, hint = OID_MAP[oid_str]
        return {"name": name, "category": cat, "hint": hint, "known": True}

    # Tenta match por prefixo (para entradas indexadas como 1.3.6.1.2.1.2.2.1.10.1)
    for prefix, (name, cat, hint) in OID_MAP.items():
        if oid_str.startswith(prefix + ".") or oid_str.startswith(prefix):
            suffix = oid_str[len(prefix):].lstrip(".")
            label = f"{name}.{suffix}" if suffix else name
            return {"name": label, "category": cat, "hint": hint, "known": True}

    # Desconhecido — mostra apenas o OID
    parts = oid_str.rsplit(".", 2)
    return {"name": oid_str, "category": "Desconhecido", "hint": "OID não mapeado", "known": False}


def _clean(host: str) -> str:
    return (host or "").strip().split("/")[0].split(" ")[0]
