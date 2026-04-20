from pydantic import BaseModel


class BackendApiStatusResponse(BaseModel):
    configured: bool
    base_url: str | None
    health_ok: bool
    health_error: str | None
    stream_status_ok: bool
    stream_status_error: str | None
    stream_available: bool | None = None
    has_frame: bool | None = None
    frame_age_ms: float | None = None
    stale_after_ms: int | None = None
    active_camera_id: str | None = None
    last_error: str | None = None


class RelayStatusResponse(BaseModel):
    relay_public_scheme: str
    relay_public_host: str
    relay_rtmp_port: int
    relay_rtc_port: int
    relay_rtc_candidate: str
    relay_default_app: str
    relay_default_stream: str
    publish_url: str
    hls_url: str
    whep_url: str
    whip_url: str
    srs_http_api_url: str
    srs_http_server_url: str
    srs_api_ok: bool
    srs_api_error: str | None
    backend_api: BackendApiStatusResponse


class StreamPlanResponse(BaseModel):
    app_name: str
    stream_name: str
    publish_url: str
    hls_url: str
    whep_url: str
    whip_url: str
