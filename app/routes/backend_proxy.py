import asyncio
import json
from datetime import datetime, timezone

import httpx
import websockets
from fastapi import APIRouter, HTTPException, Request, Response, WebSocket
from fastapi.responses import JSONResponse

from app.core.config import settings


router = APIRouter(tags=["backend-proxy"])


@router.get("/api/v1/cameras")
@router.get("/api/v1/cameras/available")
@router.get("/api/v1/stream/status")
@router.get("/api/v1/stream/sources/usb")
@router.get("/api/v1/stream/availability")
@router.get("/api/v1/events")
@router.get("/api/v1/events/recent")
@router.get("/api/v1/events/status")
@router.get("/api/v1/live/status")
@router.get("/api/v1/vision/detections/latest")
@router.get("/api/v1/vision/objects/current")
async def proxy_backend_get(request: Request) -> JSONResponse:
    response = await _request_backend(request)
    return JSONResponse(
        status_code=response.status_code,
        content=_decode_backend_json(response),
    )


@router.get("/api/v1/events/{event_id}")
async def proxy_backend_event_detail(request: Request, event_id: int) -> JSONResponse:
    response = await _request_backend(request)
    return JSONResponse(
        status_code=response.status_code,
        content=_decode_backend_json(response),
    )


@router.post("/api/v1/cameras/select")
@router.post("/api/v1/cameras/activate")
@router.post("/api/v1/stream/select")
async def proxy_backend_post(request: Request) -> JSONResponse:
    response = await _request_backend(request)
    return JSONResponse(
        status_code=response.status_code,
        content=_decode_backend_json(response),
    )


@router.get("/api/v1/events/{event_id}/screenshots/{variant}")
async def proxy_event_screenshot(request: Request, event_id: int, variant: str) -> Response:
    response = await _request_backend(request)
    media_type = response.headers.get("content-type", "application/octet-stream")
    headers = {
        header_name: header_value
        for header_name in ("cache-control", "content-disposition", "etag", "last-modified")
        if (header_value := response.headers.get(header_name)) is not None
    }
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=media_type,
        headers=headers,
    )


@router.websocket("/api/v1/live/ws")
async def proxy_live_events_websocket(websocket: WebSocket) -> None:
    await websocket.accept()

    try:
        backend_url = f"{_get_backend_ws_base_url()}{websocket.url.path}"
        if websocket.url.query:
            backend_url = f"{backend_url}?{websocket.url.query}"
    except HTTPException as exc:
        await websocket.send_json(_build_proxy_ws_error(str(exc.detail)))
        await websocket.close(code=1011)
        return

    try:
        async with websockets.connect(
            backend_url,
            open_timeout=settings.backend_request_timeout_seconds,
            ping_interval=None,
            close_timeout=2,
        ) as backend_ws:
            client_to_backend = asyncio.create_task(
                _forward_client_ws_to_backend(websocket, backend_ws)
            )
            backend_to_client = asyncio.create_task(
                _forward_backend_ws_to_client(websocket, backend_ws)
            )

            done, pending = await asyncio.wait(
                {client_to_backend, backend_to_client},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                task.result()
    except Exception as exc:
        await _try_send_ws_error(websocket, f"Live websocket proxy failed: {exc}")
        await _try_close_ws(websocket)


async def _request_backend(request: Request) -> httpx.Response:
    backend_base_url = _get_backend_base_url()
    target_url = f"{backend_base_url}{request.url.path}"
    body = await request.body()
    headers: dict[str, str] = {}

    content_type = request.headers.get("content-type")
    if content_type:
        headers["content-type"] = content_type

    try:
        async with httpx.AsyncClient(
            timeout=settings.backend_request_timeout_seconds,
            follow_redirects=True,
        ) as client:
            return await client.request(
                request.method,
                target_url,
                params=request.query_params,
                content=body or None,
                headers=headers or None,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Backend proxy request failed: {exc}") from exc


def _get_backend_base_url() -> str:
    base_url = settings.backend_api_base_url.strip().rstrip("/")
    if not base_url:
        raise HTTPException(
            status_code=503,
            detail="BACKEND_API_BASE_URL is not configured on relay",
        )
    return base_url


def _get_backend_ws_base_url() -> str:
    base_url = _get_backend_base_url()
    if base_url.startswith("https://"):
        return f"wss://{base_url.removeprefix('https://')}"
    if base_url.startswith("http://"):
        return f"ws://{base_url.removeprefix('http://')}"
    raise HTTPException(
        status_code=503,
        detail="BACKEND_API_BASE_URL must start with http:// or https://",
    )


def _decode_backend_json(response: httpx.Response) -> dict | list:
    try:
        return response.json()
    except json.JSONDecodeError:
        return {
            "detail": response.text,
            "status_code": response.status_code,
        }


async def _forward_backend_ws_to_client(
    client_ws: WebSocket,
    backend_ws: websockets.ClientConnection,
) -> None:
    async for message in backend_ws:
        if isinstance(message, bytes):
            await client_ws.send_bytes(message)
        else:
            await client_ws.send_text(message)


async def _forward_client_ws_to_backend(
    client_ws: WebSocket,
    backend_ws: websockets.ClientConnection,
) -> None:
    while True:
        message = await client_ws.receive()
        message_type = message.get("type")

        if message_type == "websocket.disconnect":
            return

        if message_type != "websocket.receive":
            continue

        if message.get("text") is not None:
            await backend_ws.send(message["text"])
        elif message.get("bytes") is not None:
            await backend_ws.send(message["bytes"])


def _build_proxy_ws_error(detail: str) -> dict[str, str]:
    return {
        "type": "error",
        "channel": "events",
        "detail": detail,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


async def _try_send_ws_error(websocket: WebSocket, detail: str) -> None:
    try:
        await websocket.send_json(_build_proxy_ws_error(detail))
    except Exception:
        return


async def _try_close_ws(websocket: WebSocket) -> None:
    try:
        await websocket.close(code=1011)
    except Exception:
        return
