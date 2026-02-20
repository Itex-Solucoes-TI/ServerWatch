from sqlmodel import Session, select
from app.database import engine
from app.models.company import Company
from app.models.user import User, UserCompanyRole
from app.config import settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"])


def run_seed():
    with Session(engine) as session:
        if session.exec(select(Company)).first():
            return

        company = Company(name=settings.DEFAULT_COMPANY_NAME, slug="default")
        session.add(company)
        session.flush()

        user = User(
            name="Administrador",
            email=settings.DEFAULT_ADMIN_EMAIL,
            password_hash=pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD),
            is_superadmin=True,
        )
        session.add(user)
        session.flush()

        role = UserCompanyRole(user_id=user.id, company_id=company.id, role="ADMIN")
        session.add(role)
        session.commit()
        print(f"✅ Seed: empresa '{company.name}' e usuário '{user.email}' criados.")
