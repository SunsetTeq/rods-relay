from fastapi import APIRouter, Header, HTTPException, Response, status

from app.core.config import settings
from app.schemas.camera import (
    CameraCommandCompletePayload,
    CameraCommandResponse,
    CameraStateSyncPayload,
    RelayCameraStateResponse,
)
from app.services.events.provider import get_relay_event_repository


router = APIRouter(prefix="/api/v1/internal/cameras", tags=["internal-cameras"])


@router.put("/state", response_model=RelayCameraStateResponse)
def upsert_camera_state(
    payload: CameraStateSyncPayload,
    authorization: str | None = Header(default=None),
) -> RelayCameraStateResponse:
    _verify_ingest_token(authorization)
    repository = get_relay_event_repository()
    state = repository.upsert_camera_state(
        source_id=payload.source_id,
        state=payload.model_dump(),
    )
    return RelayCameraStateResponse(**state)


@router.get("/commands/next", response_model=CameraCommandResponse)
def claim_next_camera_command(
    source_id: str,
    authorization: str | None = Header(default=None),
) -> CameraCommandResponse | Response:
    _verify_ingest_token(authorization)
    repository = get_relay_event_repository()
    command = repository.claim_next_camera_command(
        source_id=source_id,
        retry_after_seconds=settings.camera_command_retry_after_seconds,
    )
    if command is None:
        return Response(status_code=204)
    return CameraCommandResponse(**command)


@router.post("/commands/{command_id}/complete", response_model=CameraCommandResponse)
def complete_camera_command(
    command_id: int,
    payload: CameraCommandCompletePayload,
    authorization: str | None = Header(default=None),
) -> CameraCommandResponse:
    _verify_ingest_token(authorization)
    repository = get_relay_event_repository()

    if payload.state is not None:
        repository.upsert_camera_state(
            source_id=payload.state.source_id,
            state=payload.state.model_dump(),
        )

    command = repository.complete_camera_command(
        command_id=command_id,
        ok=payload.ok,
        error=payload.error,
        result=payload.state.model_dump() if payload.state is not None else None,
    )
    if command is None:
        raise HTTPException(status_code=404, detail="Camera command not found")
    return CameraCommandResponse(**command)


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
