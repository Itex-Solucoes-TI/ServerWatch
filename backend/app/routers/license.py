from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel

from app.deps import get_session, get_current_user
from app.models.license import InstallationLicense
from app.services.license_service import validate_token

router = APIRouter(prefix="/license", tags=["license"])


@router.get("/status")
def status(
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    lic = session.exec(select(InstallationLicense).limit(1)).first()
    today = date.today()
    needs_license = not lic or not (lic.valid_until and lic.valid_until >= today)
    return {
        "needs_license": needs_license,
        "cnpj": lic.cnpj if lic else None,
        "valid_until": lic.valid_until.isoformat() if lic and lic.valid_until else None,
    }


class ActivateRequest(BaseModel):
    token: str


@router.post("/activate")
def activate(
    data: ActivateRequest,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    result = validate_token(data.token)
    if not result:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    cnpj, valid_until = result

    lic = session.exec(select(InstallationLicense).limit(1)).first()
    if lic:
        lic.cnpj = cnpj
        lic.valid_until = valid_until
    else:
        lic = InstallationLicense(cnpj=cnpj, valid_until=valid_until)
    session.add(lic)
    session.commit()

    return {"ok": True, "cnpj": cnpj, "valid_until": valid_until.isoformat()}


@router.delete("/")
def remove(
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    lic = session.exec(select(InstallationLicense).limit(1)).first()
    if lic:
        session.delete(lic)
        session.commit()
    return {"ok": True}
