from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RODS Relay"
    app_version: str = "0.1.0"
    api_port: int = 8000

    relay_public_scheme: str = "https"
    relay_public_host: str = "relay.example.com"
    relay_rtmp_port: int = 1935
    relay_rtc_port: int = 8000
    relay_rtc_candidate: str = ""
    relay_default_app: str = "live"
    relay_default_stream: str = "rods"
    relay_default_source_id: str = "rods-backend"

    srs_http_api_url: str = "http://srs:1985"
    srs_http_server_url: str = "http://srs:8080"
    events_database_path: str = "data/relay-events.db"
    events_storage_dir: str = "data/event-screenshots"
    relay_ingest_token: str = ""
    live_ping_interval_seconds: int = 15
    camera_command_retry_after_seconds: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
