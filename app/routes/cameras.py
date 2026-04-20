from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.camera import (
    CameraCommandResponse,
    CameraSelectRequest,
    RelayCameraStateResponse,
)
from app.services.events.provider import get_relay_event_repository


router = APIRouter(prefix="/api/v1/cameras", tags=["cameras"])


@router.get("", response_model=RelayCameraStateResponse)
def get_cameras_state(
    source_id: str = Query(default=settings.relay_default_source_id),
) -> RelayCameraStateResponse:
    repository = get_relay_event_repository()
    state = repository.get_camera_state(source_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Camera state is not available yet")
    return RelayCameraStateResponse(**state)


@router.post("/select", response_model=CameraCommandResponse)
def select_camera(payload: CameraSelectRequest) -> CameraCommandResponse:
    repository = get_relay_event_repository()
    source_id = (payload.source_id or settings.relay_default_source_id).strip()
    state = repository.get_camera_state(source_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Camera state is not available yet")

    available_camera_ids = {
        str(item["camera_id"])
        for item in state.get("cameras", [])
    }
    if payload.camera_id not in available_camera_ids:
        raise HTTPException(status_code=422, detail="Unknown camera_id for this source")

    command = repository.create_camera_command(
        source_id=source_id,
        command_type="select_camera",
        payload={"camera_id": payload.camera_id},
    )
    return CameraCommandResponse(**command)


@router.get("/commands/{command_id}", response_model=CameraCommandResponse)
def get_camera_command(command_id: int) -> CameraCommandResponse:
    repository = get_relay_event_repository()
    command = repository.get_camera_command(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Camera command not found")
    return CameraCommandResponse(**command)
