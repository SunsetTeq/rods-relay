from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.relay import RelayStatusResponse, StreamPlanResponse


router = APIRouter(prefix="/api/v1/relay", tags=["relay"])


@router.get("/status", response_model=RelayStatusResponse)
async def get_relay_status() -> RelayStatusResponse:
    srs_api_ok = False
    srs_api_error = None

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
        srs_http_api_url=settings.srs_http_api_url,
        srs_http_server_url=settings.srs_http_server_url,
        srs_api_ok=srs_api_ok,
        srs_api_error=srs_api_error,
    )


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
