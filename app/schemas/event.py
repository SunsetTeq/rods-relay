from typing import Literal

from pydantic import BaseModel


class EventResponse(BaseModel):
    id: int
    source_id: str
    source_event_id: int
    event_type: str
    class_name: str
    class_id: int | None
    track_id: int | None = None
    confidence: float
    state_key: str
    first_seen_frame_id: int
    confirmed_frame_id: int
    last_seen_frame_id: int
    stable_frames_required: int
    absent_frames_required: int
    cooldown_seconds: int
    source_frame_width: int | None
    source_frame_height: int | None
    frame_timestamp: str
    created_at: str
    updated_at: str | None = None
    received_at: str
    screenshot_annotated_url: str | None = None


class EventPaginationResponse(BaseModel):
    limit: int
    before_id: int | None = None
    after_id: int | None = None
    order: Literal["asc", "desc"]
    count: int
    has_more: bool
    next_before_id: int | None = None
    next_after_id: int | None = None
    oldest_id: int | None = None
    newest_id: int | None = None


class EventListResponse(BaseModel):
    items: list[EventResponse]
    pagination: EventPaginationResponse


class LiveEventStatusResponse(BaseModel):
    is_running: bool
    subscribers: int


class IngestEventItem(BaseModel):
    id: int
    event_type: str
    class_name: str
    class_id: int | None
    track_id: int | None = None
    confidence: float
    state_key: str
    first_seen_frame_id: int
    confirmed_frame_id: int
    last_seen_frame_id: int
    stable_frames_required: int
    absent_frames_required: int
    cooldown_seconds: int
    source_frame_width: int | None
    source_frame_height: int | None
    frame_timestamp: str
    created_at: str
    updated_at: str | None = None


class IngestEventPayload(BaseModel):
    source_id: str
    event: IngestEventItem
