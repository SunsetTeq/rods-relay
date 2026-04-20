from functools import lru_cache

from app.core.config import settings
from app.db.repository import RelayEventRepository


@lru_cache(maxsize=1)
def get_relay_event_repository() -> RelayEventRepository:
    return RelayEventRepository(
        database_path=settings.events_database_path,
    )
