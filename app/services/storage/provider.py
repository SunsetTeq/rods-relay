from functools import lru_cache

from app.core.config import settings
from app.services.storage.screenshot_service import RelayScreenshotService


@lru_cache(maxsize=1)
def get_relay_screenshot_service() -> RelayScreenshotService:
    return RelayScreenshotService(
        base_dir=settings.events_storage_dir,
    )
