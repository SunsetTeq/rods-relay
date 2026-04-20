from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import settings
from app.schemas.event import EventResponse, IngestEventPayload
from app.services.events.provider import get_relay_event_repository
from app.services.events.serialization import serialize_event_row
from app.services.live_event_provider import live_event_service
from app.services.storage.provider import get_relay_screenshot_service


router = APIRouter(prefix="/api/v1/internal/events", tags=["internal-events"])


@router.post("", response_model=EventResponse)
async def ingest_event(
    payload: IngestEventPayload,
    authorization: str | None = Header(default=None),
) -> EventResponse:
    _verify_ingest_token(authorization)
    relay_event_repository = get_relay_event_repository()

    relay_event_id, created = relay_event_repository.upsert_event(
        source_id=payload.source_id,
        source_event=payload.event.model_dump(),
    )

    row = relay_event_repository.get_event_by_id(relay_event_id)
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to load stored relay event")

    serialized_event = serialize_event_row(row)
    live_event_service.publish_from_thread(
        live_event_service.build_message(
            message_type="event_confirmed" if created else "event_updated",
            event=serialized_event,
        )
    )

    return EventResponse(**serialized_event)


@router.put("/{event_id}/screenshots/annotated", response_model=EventResponse)
async def upload_annotated_screenshot(
    event_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
    content_type: str | None = Header(default=None, alias="Content-Type"),
    frame_timestamp: str | None = Header(default=None, alias="X-Frame-Timestamp"),
) -> EventResponse:
    _verify_ingest_token(authorization)
    relay_event_repository = get_relay_event_repository()
    relay_screenshot_service = get_relay_screenshot_service()

    row = relay_event_repository.get_event_by_id(event_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Relay event not found")

    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="Annotated screenshot body is empty")

    screenshot_annotated_path = relay_screenshot_service.save_event_bytes(
        event_id=event_id,
        variant="annotated",
        content=content,
        frame_timestamp=frame_timestamp or row.get("frame_timestamp"),
        content_type=content_type,
    )
    relay_event_repository.update_event_screenshots(
        event_id=event_id,
        screenshot_annotated_path=screenshot_annotated_path,
    )

    updated_row = relay_event_repository.get_event_by_id(event_id)
    if updated_row is None:
        raise HTTPException(status_code=500, detail="Failed to load updated relay event")

    serialized_event = serialize_event_row(updated_row)
    live_event_service.publish_from_thread(
        live_event_service.build_message(
            message_type="event_updated",
            event=serialized_event,
            extra={"updated_fields": ["screenshot_annotated_url"]},
        )
    )

    return EventResponse(**serialized_event)


def _verify_ingest_token(authorization: str | None) -> None:
    expected_token = settings.relay_ingest_token.strip()
    if not expected_token:
        return

    expected_header = f"Bearer {expected_token}"
    if authorization != expected_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid relay ingest token",
        )
