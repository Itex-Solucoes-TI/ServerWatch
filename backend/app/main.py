from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import create_db_and_tables
from app.seed import run_seed
from app.scheduler import start_scheduler
from app.config import settings
from app.routers import auth, companies, users, servers, routers_api, license
from app.routers import network, topology, checks, notifications, company_settings
from app.routers import docker_api, health, dashboard, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    run_seed()
    start_scheduler()
    yield


app = FastAPI(title="ServerWatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(license.router, prefix="/api")
app.include_router(companies.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(servers.router, prefix="/api")
app.include_router(routers_api.router, prefix="/api")
app.include_router(network.router, prefix="/api")
app.include_router(topology.router, prefix="/api")
app.include_router(checks.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(company_settings.router, prefix="/api")
app.include_router(docker_api.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(ws.router, prefix="/api")
