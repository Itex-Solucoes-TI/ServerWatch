from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.deps import get_session, get_company_id, require_role
from app.models.company_settings import CompanySettings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings(
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    s = session.exec(select(CompanySettings).where(CompanySettings.company_id == company_id)).first()
    if not s:
        s = CompanySettings(company_id=company_id)
        session.add(s)
        session.commit()
        session.refresh(s)
    return s


@router.put("")
def update_settings(
    data: dict,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    s = session.exec(select(CompanySettings).where(CompanySettings.company_id == company_id)).first()
    if not s:
        s = CompanySettings(company_id=company_id)
        session.add(s)
        session.flush()
    for k in ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_from", "smtp_tls", "zapi_instance_id", "zapi_token", "zapi_client_token"]:
        if k in data:
            setattr(s, k, data[k])
    session.add(s)
    session.commit()
    session.refresh(s)
    return s
