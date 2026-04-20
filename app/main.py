from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.routes.cameras import router as cameras_router
from app.routes.events import router as events_router
from app.routes.health import router as health_router
from app.routes.internal_cameras import router as internal_cameras_router
from app.routes.internal_events import router as internal_events_router
from app.routes.internal_vision import router as internal_vision_router
from app.routes.live import router as live_router
from app.routes.relay import router as relay_router
from app.routes.vision import router as vision_router
from app.services.live_event_provider import live_event_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    live_event_service.start()
    yield
    live_event_service.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(relay_router)
app.include_router(cameras_router)
app.include_router(events_router)
app.include_router(live_router)
app.include_router(vision_router)
app.include_router(internal_cameras_router)
app.include_router(internal_events_router)
app.include_router(internal_vision_router)
