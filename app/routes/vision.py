from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.detection import (
    CurrentObjectsResponse,
    DetectionFrameResponse,
    VisionStatusResponse,
)
from app.services.events.provider import get_relay_event_repository


router = APIRouter(prefix="/api/v1/vision", tags=["vision"])


@router.get("/status", response_model=VisionStatusResponse)
def get_vision_status(
    source_id: str = Query(default=settings.relay_default_source_id),
) -> VisionStatusResponse:
    repository = get_relay_event_repository()
    detection_frame = repository.get_detection_frame(source_id)
    current_objects = repository.get_current_objects(source_id)

    if detection_frame is None or current_objects is None:
        return VisionStatusResponse(
            source_id=source_id,
            has_data=False,
            frame_id=0,
            frame_timestamp=None,
            detections_count=0,
            objects_count=0,
            updated_at=None,
        )

    return VisionStatusResponse(
        source_id=source_id,
        has_data=True,
        frame_id=int(detection_frame["frame_id"]),
        frame_timestamp=detection_frame.get("frame_timestamp"),
        detections_count=int(detection_frame["detections_count"]),
        objects_count=int(current_objects["objects_count"]),
        updated_at=detection_frame.get("updated_at"),
    )


@router.get("/detections/latest", response_model=DetectionFrameResponse)
def get_latest_detections(
    source_id: str = Query(default=settings.relay_default_source_id),
) -> DetectionFrameResponse:
    repository = get_relay_event_repository()
    payload = repository.get_detection_frame(source_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Detection frame is not available yet")

    return DetectionFrameResponse(
        frame_id=int(payload["frame_id"]),
        source_frame_size=payload.get("source_frame_size"),
        frame_timestamp=payload.get("frame_timestamp"),
        inference_ms=float(payload["inference_ms"]),
        detections_count=int(payload["detections_count"]),
        detections=payload.get("detections", []),
    )


@router.get("/objects/current", response_model=CurrentObjectsResponse)
def get_current_objects(
    source_id: str = Query(default=settings.relay_default_source_id),
) -> CurrentObjectsResponse:
    repository = get_relay_event_repository()
    payload = repository.get_current_objects(source_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Current objects are not available yet")

    return CurrentObjectsResponse(
        frame_id=int(payload["frame_id"]),
        frame_timestamp=payload.get("frame_timestamp"),
        objects_count=int(payload["objects_count"]),
        objects=payload.get("objects", []),
    )
