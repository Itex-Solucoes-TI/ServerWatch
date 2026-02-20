from datetime import date
from pathlib import Path

from jose import jwt, JWTError

from app.config import settings


def _get_public_key() -> str | None:
    path = settings.LICENSE_PUBLIC_KEY_PATH
    full = Path(__file__).resolve().parent.parent.parent / path
    return full.read_text() if full.exists() else None


def validate_token(token: str) -> tuple[str | None, date] | None:
    try:
        key = _get_public_key()
        if not key:
            return None
        payload = jwt.decode(token, key, algorithms=["RS256"])
        if payload.get("type") != "license":
            return None
        valid_until_str = payload.get("valid_until")
        if not valid_until_str:
            return None
        valid_until = date.fromisoformat(valid_until_str)
        if valid_until < date.today():
            return None
        cnpj = payload.get("cnpj")  # opcional, tokens antigos não têm
        return (cnpj, valid_until)
    except (JWTError, ValueError):
        return None
