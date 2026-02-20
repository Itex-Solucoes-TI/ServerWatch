from fastapi import WebSocket
import json
import asyncio

connections: list[WebSocket] = []


async def connect(ws: WebSocket):
    await ws.accept()
    connections.append(ws)


def disconnect(ws: WebSocket):
    if ws in connections:
        connections.remove(ws)


async def broadcast(event: str, data: dict):
    msg = json.dumps({"event": event, "data": data})
    dead = []
    for ws in connections:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        disconnect(ws)


def broadcast_check_update(check, result):
    asyncio.create_task(broadcast("check_update", {"check_id": check.id, "status": result.status, "message": result.message}))


def broadcast_docker_sync(server_id: int):
    asyncio.create_task(broadcast("docker_sync", {"server_id": server_id}))
