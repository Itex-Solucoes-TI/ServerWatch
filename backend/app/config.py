from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://serverwatch:serverwatch123@localhost/serverwatch"
    JWT_SECRET: str = "troque-em-producao"
    DEFAULT_COMPANY_NAME: str = "Minha Empresa"
    DEFAULT_ADMIN_EMAIL: str = "admin@empresa.com"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [x.strip() for x in self.CORS_ORIGINS.split(",") if x.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
