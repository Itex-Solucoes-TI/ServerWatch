"""
OIDs SNMP padrão por tipo de métrica.
OIDs de tráfego/interfaces são base (sem índice) - precisam de WALK para listar interfaces.
"""

# Informações gerais (GET simples)
OIDS_INFO = {
    "sysDescr":   "1.3.6.1.2.1.1.1.0",
    "sysName":    "1.3.6.1.2.1.1.5.0",
    "sysUpTime":  "1.3.6.1.2.1.1.3.0",
}

# Interfaces (WALK - retorna .ifIndex por sufixo)
OIDS_INTERFACES = {
    "ifDescr":    "1.3.6.1.2.1.2.2.1.2",   # Nome da interface (eth0, wlan0, etc.)
    "ifInOctets": "1.3.6.1.2.1.2.2.1.10",  # Bytes recebidos (IN)
    "ifOutOctets":"1.3.6.1.2.1.2.2.1.16",  # Bytes enviados (OUT)
    "ifOperStatus":"1.3.6.1.2.1.2.2.1.8",  # Status (1=up, 2=down)
}

# CPU - HOST-RESOURCES-MIB (padrão - funciona em Linux/Windows/maioria dos roteadores)
OIDS_CPU = {
    "hrProcessorLoad": "1.3.6.1.2.1.25.3.3.1.2",  # WALK - carga % por CPU
}

# CPU alternativo para roteadores sem HOST-RESOURCES-MIB
OIDS_CPU_ALT = {
    # MikroTik
    "mtxrCPUFrequency": "1.3.6.1.4.1.14988.1.1.3.14.0",
    # Cisco (sysDescr costuma ter modelo; usar WALK de entPhysicalTable)
}

# Memória - HOST-RESOURCES-MIB
OIDS_MEMORY = {
    "hrStorageType":       "1.3.6.1.2.1.25.2.3.1.2",   # Tipo de storage (RAM=.2)
    "hrStorageDescr":      "1.3.6.1.2.1.25.2.3.1.3",   # Descrição
    "hrStorageSize":       "1.3.6.1.2.1.25.2.3.1.5",   # Tamanho total (allocation units)
    "hrStorageUsed":       "1.3.6.1.2.1.25.2.3.1.6",   # Usado
    "hrStorageAllocationUnits": "1.3.6.1.2.1.25.2.3.1.4",  # Tamanho de cada unidade
}
HR_STORAGE_RAM_TYPE = "1.3.6.1.2.1.25.2.1.2"  # OID para identificar RAM no hrStorageType

# WiFi - IEEE 802.11-MIB (padrão, mas raramente suportado diretamente)
OIDS_WIFI = {
    "dot11StationConfigEntry": "1.2.840.10036.1.1.1",
}

# WiFi alternativo - mais comum (contagem por interface wireless)
OIDS_WIFI_CLIENTS = {
    # MikroTik - clientes associados em cada interface wireless
    "mtxrWlStatIndex":     "1.3.6.1.4.1.14988.1.1.1.2.1.1",
    "mtxrWlStatTxRate":    "1.3.6.1.4.1.14988.1.1.1.2.1.2",
    "mtxrWlStatMacAddr":   "1.3.6.1.4.1.14988.1.1.1.2.1.3",
    # OID genérico: interfaces wireless ativas (ifInOctets em wlan*)
    # Fallback: contar entradas em dot11AssociationEntry
    "dot11AssocCount":     "1.2.840.10036.2.1.1.1",
}

# Mapeamento tipo -> OID base para uso dinâmico
METRIC_DEFAULT_OIDS = {
    "TRAFFIC":      {"in": OIDS_INTERFACES["ifInOctets"], "out": OIDS_INTERFACES["ifOutOctets"], "descr": OIDS_INTERFACES["ifDescr"]},
    "CPU":          {"load": OIDS_CPU["hrProcessorLoad"]},
    "MEMORY":       {k: v for k, v in OIDS_MEMORY.items()},
    "WIFI_CLIENTS": {"mikrotik": OIDS_WIFI_CLIENTS["mtxrWlStatIndex"]},
    "UPTIME":       {"uptime": OIDS_INFO["sysUpTime"]},
}

# Labels amigáveis
METRIC_LABELS = {
    "TRAFFIC":      "Tráfego de Rede",
    "CPU":          "CPU",
    "MEMORY":       "Memória",
    "WIFI_CLIENTS": "Clientes WiFi",
    "UPTIME":       "Uptime",
}

METRIC_UNITS = {
    "TRAFFIC_IN":   "bytes_sec",
    "TRAFFIC_OUT":  "bytes_sec",
    "CPU":          "percent",
    "MEMORY":       "percent",
    "WIFI_CLIENTS": "count",
    "UPTIME":       "seconds",
}
