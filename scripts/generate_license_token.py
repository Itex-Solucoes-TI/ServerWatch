#!/usr/bin/env python3
"""
Gera token de licença. Usa a chave PRIVADA (nunca no servidor do cliente).
Uso: python scripts/generate_license_token.py <cnpj14digitos> <validade YYYY-MM-DD>
Ex:  python scripts/generate_license_token.py 12882279000163 2026-12-31
"""
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_PATH = ROOT / "backend" / "keys" / "license_private.pem"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    cnpj_raw = "".join(c for c in sys.argv[1] if c.isdigit())
    if len(cnpj_raw) != 14:
        print("CNPJ deve ter 14 dígitos")
        sys.exit(1)

    try:
        valid_until = date.fromisoformat(sys.argv[2])
    except ValueError:
        print("Validade deve ser YYYY-MM-DD")
        sys.exit(1)

    if not PRIVATE_PATH.exists():
        print("Chave privada não encontrada. Execute scripts/generate_license_keys.py primeiro.")
        sys.exit(1)

    try:
        from jose import jwt
    except ImportError:
        print("Instale: pip install python-jose[cryptography]")
        sys.exit(1)

    private_key = PRIVATE_PATH.read_text()

    payload = {
        "cnpj": cnpj_raw,
        "valid_until": valid_until.isoformat(),
        "type": "license",
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")

    print(token)


if __name__ == "__main__":
    main()
