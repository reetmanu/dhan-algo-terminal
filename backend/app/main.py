from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from app.db.base import engine, Base
from app.api import router_config, router_strategies, router_dashboard, router_control
from app.workers.engine import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Dhan Algo Terminal...")
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    logger.info("Scheduler started.")
    yield
    # Shutdown
    stop_scheduler()
    logger.info("Scheduler stopped.")


app = FastAPI(
    title="Dhan Algo Terminal",
    version="0.1.0",
    description="NSE/BSE Technical Indicator based Algo Trading Platform",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(router_config.router, prefix="/api/config", tags=["config"])
app.include_router(router_strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(router_dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(router_control.router, prefix="/api/control", tags=["control"])

# Serve frontend static files (if built)
if os.path.exists("/app/static"):
    app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "dhan-algo-terminal"}
