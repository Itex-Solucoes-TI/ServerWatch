from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select
from app.deps import get_session, get_current_user, require_role
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyRead
from app.services.audit_service import log

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyRead])
def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if user.is_superadmin:
        items = session.exec(select(Company).where(Company.active == True).offset(skip).limit(limit)).all()
    else:
        from app.models.user import UserCompanyRole
        roles = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == user.id)).all()
        ids = [r.company_id for r in roles]
        items = session.exec(select(Company).where(Company.id.in_(ids), Company.active == True).offset(skip).limit(limit)).all()
    return items


@router.post("", response_model=CompanyRead)
def create_company(
    data: CompanyCreate,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from app.models.user import UserCompanyRole
    if not user.is_superadmin:
        admin_role = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == user.id, UserCompanyRole.role == "ADMIN")).first()
        if not admin_role:
            raise HTTPException(403, "Sem permissão")
    company = Company(**data.model_dump())
    session.add(company)
    session.flush()
    # vincula todos os superadmins como ADMIN (incluindo o criador se for superadmin)
    from app.models.user import User as UserModel
    superadmins = session.exec(select(UserModel).where(UserModel.is_superadmin == True, UserModel.active == True)).all()
    superadmin_ids = {sa.id for sa in superadmins}
    for sa in superadmins:
        session.add(UserCompanyRole(user_id=sa.id, company_id=company.id, role="ADMIN"))
    # vincula o criador se não for superadmin
    if not user.is_superadmin:
        session.add(UserCompanyRole(user_id=user.id, company_id=company.id, role="ADMIN"))
    log(session, user.id, "CREATE", company.id, "COMPANY", company.id)
    session.commit()
    session.refresh(company)
    return company


@router.get("/{id}", response_model=CompanyRead)
def get_company(id: int, user=Depends(get_current_user), session: Session = Depends(get_session)):
    company = session.get(Company, id)
    if not company or not company.active:
        raise HTTPException(404, "Não encontrado")
    return company


@router.put("/{id}", response_model=CompanyRead)
def update_company(
    id: int,
    data: CompanyUpdate,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    company = session.get(Company, id)
    if not company:
        raise HTTPException(404, "Não encontrado")
    from app.models.user import UserCompanyRole
    if not user.is_superadmin:
        r = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == user.id, UserCompanyRole.company_id == id, UserCompanyRole.role == "ADMIN")).first()
        if not r:
            raise HTTPException(403, "Sem permissão")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(company, k, v)
    log(session, user.id, "UPDATE", id, "COMPANY", id)
    session.commit()
    session.refresh(company)
    return company
