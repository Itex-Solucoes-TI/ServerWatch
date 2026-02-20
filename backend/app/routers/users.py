from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select
from app.deps import get_session, get_company_id, require_role, get_current_user
from app.models.user import User, UserCompanyRole
from app.models.company import Company
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.audit_service import log
from passlib.context import CryptContext

router = APIRouter(prefix="/users", tags=["users"])
pwd = CryptContext(schemes=["bcrypt"])


def _get_admin_company_ids(user, session) -> set[int]:
    if user.is_superadmin:
        return {c.id for c in session.exec(select(Company)).all()}
    roles = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == user.id, UserCompanyRole.role == "ADMIN")).all()
    return {r.company_id for r in roles}


@router.get("/my-companies")
def my_admin_companies(
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Retorna empresas onde o usuário logado é ADMIN (para usar no form de usuário)."""
    if user.is_superadmin:
        companies = session.exec(select(Company).where(Company.active == True)).all()
    else:
        roles = session.exec(
            select(UserCompanyRole).where(UserCompanyRole.user_id == user.id, UserCompanyRole.role == "ADMIN")
        ).all()
        ids = [r.company_id for r in roles]
        companies = session.exec(select(Company).where(Company.id.in_(ids), Company.active == True)).all()
    return [{"id": c.id, "name": c.name} for c in companies]


@router.get("", response_model=list[UserRead])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    roles = session.exec(select(UserCompanyRole).where(UserCompanyRole.company_id == company_id)).all()
    role_by_user = {r.user_id: r.role for r in roles}
    user_ids = [r.user_id for r in roles]
    items = session.exec(select(User).where(User.id.in_(user_ids), User.active == True).offset(skip).limit(limit)).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "role": role_by_user.get(u.id), "is_superadmin": u.is_superadmin} for u in items]


@router.post("", response_model=UserRead)
def create_user(
    data: UserCreate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    existing = session.exec(select(User).where(User.email == data.email)).first()
    if existing:
        raise HTTPException(400, "Email já existe")
    u = User(name=data.name, email=data.email, password_hash=pwd.hash(data.password))
    session.add(u)
    session.flush()

    # vínculos: usa a lista company_roles se fornecida, senão vincula só à empresa atual
    company_roles = data.company_roles if data.company_roles else [{"company_id": company_id, "role": data.role}]
    admin_company_ids = _get_admin_company_ids(user, session)
    role_na_empresa_atual = data.role
    for cr in company_roles:
        cid = cr["company_id"] if isinstance(cr, dict) else cr.company_id
        crole = cr["role"] if isinstance(cr, dict) else cr.role
        if cid not in admin_company_ids and not user.is_superadmin:
            continue  # não pode dar permissão em empresa que não administra
        existing_role = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == u.id, UserCompanyRole.company_id == cid)).first()
        if not existing_role:
            session.add(UserCompanyRole(user_id=u.id, company_id=cid, role=crole))
        if cid == company_id:
            role_na_empresa_atual = crole

    log(session, user.id, "CREATE", company_id, "USER", u.id)
    session.commit()
    session.refresh(u)
    return {"id": u.id, "name": u.name, "email": u.email, "role": role_na_empresa_atual}


@router.get("/{id}", response_model=UserRead)
def get_user(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN", "OPERATOR", "VIEWER")),
    session: Session = Depends(get_session),
):
    role = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == id, UserCompanyRole.company_id == company_id)).first()
    if not role:
        raise HTTPException(404, "Não encontrado")
    u = session.get(User, id)
    return {"id": u.id, "name": u.name, "email": u.email, "role": role.role}


@router.get("/{id}/companies")
def get_user_companies(
    id: int,
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    """Retorna todos os vínculos empresa+role do usuário."""
    roles = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == id)).all()
    return [{"company_id": r.company_id, "role": r.role} for r in roles]


@router.put("/{id}", response_model=UserRead)
def update_user(
    id: int,
    data: UserUpdate,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    role = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == id, UserCompanyRole.company_id == company_id)).first()
    if not role:
        raise HTTPException(404, "Não encontrado")
    u = session.get(User, id)
    if data.name is not None:
        u.name = data.name
    if data.email is not None:
        if data.email != u.email:
            existing = session.exec(select(User).where(User.email == data.email)).first()
            if existing:
                raise HTTPException(400, "Email já existe")
            u.email = data.email
    if data.password:
        u.password_hash = pwd.hash(data.password)
    if data.role is not None:
        role.role = data.role
        session.add(role)

    # atualiza vínculos por empresa se fornecidos
    if data.company_roles is not None:
        admin_ids = _get_admin_company_ids(user, session)
        # company_roles contém apenas as empresas marcadas (ativas)
        active_ids = {cr.company_id for cr in data.company_roles if cr.company_id in admin_ids or user.is_superadmin}

        # remove vínculos desmarcados (que o criador administra)
        existing_roles = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == id)).all()
        for er in existing_roles:
            if er.company_id not in admin_ids and not user.is_superadmin:
                continue  # não mexe em empresas que não administra
            if er.company_id not in active_ids:
                session.delete(er)

        # adiciona/atualiza os marcados
        for cr in data.company_roles:
            if cr.company_id not in admin_ids and not user.is_superadmin:
                continue
            existing_role = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == id, UserCompanyRole.company_id == cr.company_id)).first()
            if existing_role:
                existing_role.role = cr.role
                session.add(existing_role)
            else:
                session.add(UserCompanyRole(user_id=id, company_id=cr.company_id, role=cr.role))

    log(session, user.id, "UPDATE", company_id, "USER", id)
    session.commit()
    session.refresh(u)
    session.refresh(role)
    return {"id": u.id, "name": u.name, "email": u.email, "role": role.role, "is_superadmin": u.is_superadmin}


@router.delete("/{id}")
def delete_user(
    id: int,
    company_id: int = Depends(get_company_id),
    user=Depends(require_role("ADMIN")),
    session: Session = Depends(get_session),
):
    role = session.exec(select(UserCompanyRole).where(UserCompanyRole.user_id == id, UserCompanyRole.company_id == company_id)).first()
    if not role:
        raise HTTPException(404, "Não encontrado")
    target = session.get(User, id)
    if target and target.is_superadmin:
        raise HTTPException(403, "Não é possível remover um superadmin")
    if user.id == id:
        raise HTTPException(400, "Não é possível remover seu próprio usuário")
    session.delete(role)
    log(session, user.id, "DELETE", company_id, "USER", id)
    session.commit()
    return {"ok": True}
