from app.models.audit_log import AuditLog
from sqlmodel import Session


def log(session: Session, user_id: int, action: str, company_id: int = None, entity_type: str = None, entity_id: int = None, details: str = None):
    session.add(AuditLog(
        user_id=user_id,
        action=action,
        company_id=company_id,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    ))
