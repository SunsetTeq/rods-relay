# RODS Relay

External relay layer for the RODS system.

This repository hosts:

- `SRS` as the media relay server
- `Caddy` for HTTPS termination and routing
- a minimal `FastAPI` control API for health checks and stream URL planning

## Architecture

```text
rods-backend (home PC with camera)
  -> RTMP publish -> rods-relay (SRS)
  -> event/API relay -> future extension

rods-mobile (Expo Go)
  -> HTTPS HLS playback from rods-relay
  -> HTTPS API requests to rods-relay
```

## Quick Start

1. Create env:

```bash
cp .env.example .env
```

2. Set a public hostname in `.env`.

Recommended quick option on a fresh VPS:

```env
RELAY_PUBLIC_HOST=<your-server-ip>.sslip.io
```

3. Start the stack:

```bash
docker compose up --build -d
```

4. Verify:

```bash
curl https://<your-host>/health
curl https://<your-host>/api/v1/relay/status
curl https://<your-host>/api/v1/relay/streams/rods
```

## Today’s Test Flow

### 1. On the relay server

Bring up the stack:

```bash
docker compose up --build -d
```

### 2. On the home machine running rods-backend

Set the relay publish URL:

```env
RELAY_ENABLED=true
RELAY_PUBLISH_URL=rtmp://<your-host>:1935/live/rods
RELAY_OUTPUT_VARIANT=annotated
RELAY_WIDTH=1280
RELAY_HEIGHT=720
RELAY_FPS=30
RELAY_VIDEO_BITRATE_KBPS=2500
RELAY_H264_PRESET=veryfast
RELAY_FFMPEG_BIN=ffmpeg
```

Then start `rods-backend`.

### 3. Playback

Open:

```text
https://<your-host>/live/rods.m3u8
```

Or fetch the generated URLs:

```bash
curl https://<your-host>/api/v1/relay/streams/rods
```

The HLS playlist appears only after SRS receives a valid RTMP publish.
If `/live/rods.m3u8` returns `Not Found`, check that the edge backend is publishing
to `rtmp://<your-host>:1935/live/rods` and that the relay server exposes port `1935`
from the `srs` service, not from `caddy`.

### 4. Troubleshooting

Inspect the relay containers:

```bash
docker compose ps
docker compose logs -f srs
docker compose logs -f caddy
docker compose logs -f api
```

Common checks:

- `https://<your-host>/health` should return `200`.
- `https://<your-host>/api/v1/relay/status` should report `srs_api_ok=true`.
- `rtmp://<your-host>:1935/live/rods` must terminate on `SRS`, otherwise `ffmpeg`
  on `rods-backend` will fail with `Cannot read RTMP handshake response`.
- `https://<your-host>/live/rods.m3u8` will return `404 Not Found` until the first
  successful RTMP publish reaches `SRS`.

## Notes

- `RTMP` is used for ingest from the home edge device because it is simple and reliable.
- `HLS` is used for Expo Go playback because it is supported by iOS and Expo-friendly players.
- This setup is optimized for reliable `720p/30fps` transport, not ultra-low latency.
- Expect HLS latency in the range of a few seconds.
