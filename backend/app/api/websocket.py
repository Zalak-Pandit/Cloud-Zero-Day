import asyncio
import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

_connections: Set[WebSocket] = set()


@router.websocket("/threats")
async def threat_stream(websocket: WebSocket):
    global _connections
    await websocket.accept()
    _connections.add(websocket)
    logger.info(f"WS client connected. Total: {len(_connections)}")
    try:
        await websocket.send_json({"type": "connected", "message": "CloudSentinel live feed active"})
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _connections.discard(websocket)
        logger.info(f"WS client disconnected. Total: {len(_connections)}")


async def broadcast_event(payload: dict):
    global _connections
    if not _connections:
        return
    dead = set()
    msg = json.dumps(payload)
    for ws in list(_connections):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    _connections -= dead