from jose import jwt
from datetime import datetime, timedelta
from app.config import settings


def create_tokens(user_id: int) -> dict:
    now = datetime.utcnow()
    access_payload = {
        "user_id": user_id,
        "exp": now + timedelta(minutes=15),
        "type": "access",
    }
    refresh_payload = {
        "user_id": user_id,
        "exp": now + timedelta(days=7),
        "type": "refresh",
    }
    return {
        "access_token": jwt.encode(
            access_payload, settings.JWT_SECRET, algorithm="HS256"
        ),
        "refresh_token": jwt.encode(
            refresh_payload, settings.JWT_SECRET, algorithm="HS256"
        ),
    }
