from typing import Any, Literal

from pydantic import BaseModel


class RelayCameraStatusResponse(BaseModel):
    is_running: bool
    source_type: str
    source: str
    active_camera_id: str | None = None
    frame_width: int | None = None
    frame_height: int | None = None
    target_fps: int | None = None
    actual_fps: float = 0.0
    frames_read: int = 0
    read_failures: int = 0
    last_error: str | None = None


class RelayCameraListItemResponse(BaseModel):
    camera_id: str
    source_type: str
    source: str
    label: str
    name: str | None = None
    is_active: bool
    is_available: bool
    frame_width: int | None = None
    frame_height: int | None = None


class RelayCameraStateResponse(BaseModel):
    source_id: str
    active_camera_id: str | None = None
    active_camera: RelayCameraStatusResponse | None = None
    cameras: list[RelayCameraListItemResponse]
    updated_at: str | None = None


class CameraSelectRequest(BaseModel):
    camera_id: str
    source_id: str | None = None


class CameraCommandPayload(BaseModel):
    camera_id: str


class CameraCommandResponse(BaseModel):
    id: int
    source_id: str
    command_type: Literal["select_camera"]
    status: Literal["pending", "sent", "completed", "failed"]
    payload: CameraCommandPayload
    attempts: int
    created_at: str
    updated_at: str
    completed_at: str | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


class CameraStateSyncPayload(BaseModel):
    source_id: str
    active_camera_id: str | None = None
    active_camera: RelayCameraStatusResponse | None = None
    cameras: list[RelayCameraListItemResponse]


class CameraCommandCompletePayload(BaseModel):
    ok: bool
    error: str | None = None
    state: CameraStateSyncPayload | None = None
