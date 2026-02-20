from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.deps import get_session, get_current_user
from app.schemas.auth import LoginRequest, RefreshRequest, LoginResponse, SwitchRequest
from app.services.auth_service import create_tokens
from app.models.user import User, UserCompanyRole
from app.models.company import Company
from app.models.license import InstallationLicense
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    if not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    roles = session.exec(
        select(UserCompanyRole).where(UserCompanyRole.user_id == user.id)
    ).all()
    company_ids = [r.company_id for r in roles]
    companies = session.exec(
        select(Company).where(Company.id.in_(company_ids), Company.active == True)
    ).all()

    role_map = {r.company_id: r.role for r in roles}
    today = date.today()
    lic = session.exec(select(InstallationLicense).limit(1)).first()
    needs_license = not lic or not (lic.valid_until and lic.valid_until >= today)

    tokens = create_tokens(user.id)
    companies_data = [
        {
            "id": c.id, "name": c.name, "slug": c.slug, "role": role_map.get(c.id),
            "license_valid": not needs_license,
            "license_valid_until": lic.valid_until.isoformat() if lic and lic.valid_until else None,
        }
        for c in companies
    ]
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_superadmin": user.is_superadmin,
        },
        companies=companies_data,
        needs_license=needs_license,
    )


@router.post("/switch")
def switch_company(
    data: SwitchRequest,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    company_id = data.company_id
    role = session.exec(
        select(UserCompanyRole).where(UserCompanyRole.user_id == user.id, UserCompanyRole.company_id == company_id)
    ).first()
    if not role:
        if not user.is_superadmin:
            raise HTTPException(403, "Sem acesso a esta empresa")
        # superadmin: vincula automaticamente como ADMIN
        company = session.get(Company, company_id)
        if not company:
            raise HTTPException(404, "Empresa não encontrada")
        role = UserCompanyRole(user_id=user.id, company_id=company_id, role="ADMIN")
        session.add(role)
        session.commit()
        session.refresh(role)
    tokens = create_tokens(user.id)
    return {"access_token": tokens["access_token"], "company_id": company_id, "role": role.role}


@router.post("/refresh")
def refresh(data: RefreshRequest):
    try:
        payload = jwt.decode(
            data.refresh_token, settings.JWT_SECRET, algorithms=["HS256"]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
        tokens = create_tokens(payload["user_id"])
        return {"access_token": tokens["access_token"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
