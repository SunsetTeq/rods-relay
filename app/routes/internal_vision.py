from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.schemas.detection import DetectionFrameResponse, DetectionFrameSyncPayload
from app.services.events.provider import get_relay_event_repository


router = APIRouter(prefix="/api/v1/internal/vision", tags=["internal-vision"])


@router.put("/detections/latest", response_model=DetectionFrameResponse)
def upsert_detection_frame(
    payload: DetectionFrameSyncPayload,
    authorization: str | None = Header(default=None),
) -> DetectionFrameResponse:
    _verify_ingest_token(authorization)
    repository = get_relay_event_repository()
    stored_payload = repository.upsert_detection_frame(
        source_id=payload.source_id,
        payload=payload.model_dump(exclude={"source_id"}),
    )

    return DetectionFrameResponse(
        frame_id=int(stored_payload["frame_id"]),
        source_frame_size=stored_payload.get("source_frame_size"),
        frame_timestamp=stored_payload.get("frame_timestamp"),
        inference_ms=float(stored_payload["inference_ms"]),
        detections_count=int(stored_payload["detections_count"]),
        detections=stored_payload.get("detections", []),
    )


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
