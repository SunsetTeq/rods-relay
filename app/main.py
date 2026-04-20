from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.routes.backend_proxy import router as backend_proxy_router
from app.routes.health import router as health_router
from app.routes.relay import router as relay_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(relay_router)
app.include_router(backend_proxy_router)
