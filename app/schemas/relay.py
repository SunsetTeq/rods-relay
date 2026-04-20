from pydantic import BaseModel


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


class StreamPlanResponse(BaseModel):
    app_name: str
    stream_name: str
    publish_url: str
    hls_url: str
    whep_url: str
    whip_url: str
