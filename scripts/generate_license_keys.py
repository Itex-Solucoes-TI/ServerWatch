#!/usr/bin/env python3
"""
Gera par de chaves RSA para licenças.
Execute uma vez, guarde a chave PRIVADA em local seguro (nunca no servidor do cliente).
A chave PÚBLICA vai no servidor do cliente para validar tokens.
"""
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parent.parent
KEYS_DIR = ROOT / "backend" / "keys"
PRIVATE_PATH = KEYS_DIR / "license_private.pem"
PUBLIC_PATH = KEYS_DIR / "license_public.pem"


def main():
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if PRIVATE_PATH.exists():
        print("Chaves já existem. Use scripts/generate_license_token.py para gerar tokens.")
        sys.exit(0)

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    PRIVATE_PATH.write_bytes(priv_pem)
    PUBLIC_PATH.write_bytes(pub_pem)

    print("Chaves geradas em backend/keys/")
    print("  - license_public.pem  -> inclua no deploy do cliente")
    print("  - license_private.pem -> NUNCA envie ao cliente, use para gerar tokens")
    print("")
    print("Gere tokens com: python scripts/generate_license_token.py <cnpj> <validade YYYY-MM-DD>")
