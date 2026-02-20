from sqlmodel import create_engine, Session
from app.config import settings
import subprocess
import sys

engine = create_engine(settings.DATABASE_URL, echo=False)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    """Roda alembic upgrade head para criar/atualizar tabelas."""
    import os
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Migration error: {result.stderr}")
        raise RuntimeError(f"Alembic upgrade failed: {result.stderr}")
    print("✅ Migrations aplicadas.")
