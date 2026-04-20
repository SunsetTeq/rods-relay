from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.relay import BackendApiStatusResponse, RelayStatusResponse, StreamPlanResponse


router = APIRouter(prefix="/api/v1/relay", tags=["relay"])


@router.get("/status", response_model=RelayStatusResponse)
async def get_relay_status() -> RelayStatusResponse:
    srs_api_ok = False
    srs_api_error = None
    backend_api = await _get_backend_api_status()

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.srs_http_api_url}/api/v1/versions")
            response.raise_for_status()
        srs_api_ok = True
    except Exception as exc:
        srs_api_error = str(exc)

    return RelayStatusResponse(
        relay_public_scheme=settings.relay_public_scheme,
        relay_public_host=settings.relay_public_host,
        relay_rtmp_port=settings.relay_rtmp_port,
        relay_rtc_port=settings.relay_rtc_port,
        relay_rtc_candidate=settings.relay_rtc_candidate,
        relay_default_app=settings.relay_default_app,
        relay_default_stream=settings.relay_default_stream,
        publish_url=_build_publish_url(
            app_name=settings.relay_default_app,
            stream_name=settings.relay_default_stream,
        ),
        hls_url=_build_hls_url(
            app_name=settings.relay_default_app,
            stream_name=settings.relay_default_stream,
        ),
        whep_url=_build_whep_url(
            app_name=settings.relay_default_app,
            stream_name=settings.relay_default_stream,
        ),
        whip_url=_build_whip_url(
            app_name=settings.relay_default_app,
            stream_name=settings.relay_default_stream,
        ),
        srs_http_api_url=settings.srs_http_api_url,
        srs_http_server_url=settings.srs_http_server_url,
        srs_api_ok=srs_api_ok,
        srs_api_error=srs_api_error,
        backend_api=backend_api,
    )


@router.get("/backend/video-status", response_model=BackendApiStatusResponse)
async def get_backend_video_status() -> BackendApiStatusResponse:
    return await _get_backend_api_status()


@router.get("/streams/{stream_name}", response_model=StreamPlanResponse)
def get_stream_plan(stream_name: str, app_name: str | None = None) -> StreamPlanResponse:
    normalized_stream = stream_name.strip()
    if not normalized_stream:
        raise HTTPException(status_code=400, detail="stream_name cannot be empty")

    relay_app = app_name.strip() if app_name else settings.relay_default_app

    return StreamPlanResponse(
        app_name=relay_app,
        stream_name=normalized_stream,
        publish_url=_build_publish_url(app_name=relay_app, stream_name=normalized_stream),
        hls_url=_build_hls_url(app_name=relay_app, stream_name=normalized_stream),
        whep_url=_build_whep_url(app_name=relay_app, stream_name=normalized_stream),
        whip_url=_build_whip_url(app_name=relay_app, stream_name=normalized_stream),
    )


def _build_publish_url(app_name: str, stream_name: str) -> str:
    return (
        f"rtmp://{settings.relay_public_host}:{settings.relay_rtmp_port}/"
        f"{quote(app_name)}/{quote(stream_name)}"
    )


def _build_hls_url(app_name: str, stream_name: str) -> str:
    return (
        f"{settings.relay_public_scheme}://{settings.relay_public_host}/"
        f"{quote(app_name)}/{quote(stream_name)}.m3u8"
    )


def _build_whep_url(app_name: str, stream_name: str) -> str:
    return (
        f"{settings.relay_public_scheme}://{settings.relay_public_host}/rtc/v1/whep/"
        f"?app={quote(app_name)}&stream={quote(stream_name)}"
    )


def _build_whip_url(app_name: str, stream_name: str) -> str:
    return (
        f"{settings.relay_public_scheme}://{settings.relay_public_host}/rtc/v1/whip/"
        f"?app={quote(app_name)}&stream={quote(stream_name)}"
    )


async def _get_backend_api_status() -> BackendApiStatusResponse:
    base_url = settings.backend_api_base_url.strip().rstrip("/")
    if not base_url:
        return BackendApiStatusResponse(
            configured=False,
            base_url=None,
            health_ok=False,
            health_error="BACKEND_API_BASE_URL is not configured",
            stream_status_ok=False,
            stream_status_error="BACKEND_API_BASE_URL is not configured",
        )

    health_ok = False
    health_error = None
    stream_status_ok = False
    stream_status_error = None
    stream_payload: dict | None = None

    try:
        async with httpx.AsyncClient(timeout=settings.backend_request_timeout_seconds) as client:
            health_response = await client.get(f"{base_url}/health")
            health_response.raise_for_status()
        health_ok = True
    except Exception as exc:
        health_error = str(exc)

    try:
        async with httpx.AsyncClient(timeout=settings.backend_request_timeout_seconds) as client:
            stream_response = await client.get(f"{base_url}/api/v1/stream/availability")
            stream_response.raise_for_status()
        stream_payload = stream_response.json()
        stream_status_ok = True
    except Exception as exc:
        stream_status_error = str(exc)

    return BackendApiStatusResponse(
        configured=True,
        base_url=base_url,
        health_ok=health_ok,
        health_error=health_error,
        stream_status_ok=stream_status_ok,
        stream_status_error=stream_status_error,
        stream_available=(
            bool(stream_payload.get("stream_available"))
            if isinstance(stream_payload, dict) and "stream_available" in stream_payload
            else None
        ),
        has_frame=(
            bool(stream_payload.get("has_frame"))
            if isinstance(stream_payload, dict) and "has_frame" in stream_payload
            else None
        ),
        frame_age_ms=(
            float(stream_payload["frame_age_ms"])
            if isinstance(stream_payload, dict) and stream_payload.get("frame_age_ms") is not None
            else None
        ),
        stale_after_ms=(
            int(stream_payload["stale_after_ms"])
            if isinstance(stream_payload, dict) and stream_payload.get("stale_after_ms") is not None
            else None
        ),
        active_camera_id=(
            str(stream_payload["active_camera_id"])
            if isinstance(stream_payload, dict) and stream_payload.get("active_camera_id")
            else None
        ),
        last_error=(
            str(stream_payload["last_error"])
            if isinstance(stream_payload, dict) and stream_payload.get("last_error")
            else None
        ),
    )
