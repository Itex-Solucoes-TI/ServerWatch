from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer
from jose import jwt, JWTError
from sqlmodel import Session, select
from app.config import settings
from app.database import engine
from app.models.user import User, UserCompanyRole

security = HTTPBearer()


def get_session():
    with Session(engine) as session:
        yield session


def get_current_user(
    token=Depends(security),
    session: Session = Depends(get_session),
) -> User:
    try:
        payload = jwt.decode(
            token.credentials, settings.JWT_SECRET, algorithms=["HS256"]
        )
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token inválido")
        user = session.get(User, payload["user_id"])
        if not user or not user.active:
            raise HTTPException(status_code=401, detail="Usuário inválido")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")


def get_company_id(
    x_company_id: int = Header(..., alias="X-Company-Id"),
) -> int:
    return x_company_id


def require_role(*roles):
    def checker(
        user: User = Depends(get_current_user),
        company_id: int = Depends(get_company_id),
        session: Session = Depends(get_session),
    ):
        if user.is_superadmin:
            return user
        role = session.exec(
            select(UserCompanyRole)
            .where(UserCompanyRole.user_id == user.id)
            .where(UserCompanyRole.company_id == company_id)
        ).first()
        if not role or role.role not in roles:
            raise HTTPException(status_code=403, detail="Sem permissão")
        return user

    return checker
