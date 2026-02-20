import asyncio
import queue
import threading
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.database import engine
from app.models.server import Server
from app.services.ssh_terminal_service import _verify_ws_token, run_ssh_bridge
from app.services.ws_manager import connect, disconnect

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/events")
async def websocket_events(ws: WebSocket):
    await connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        disconnect(ws)


@router.websocket("/ssh/{server_id}")
async def websocket_ssh(ws: WebSocket, server_id: int):
    await ws.accept()
    token = ws.query_params.get("token")
    company_id = ws.query_params.get("company_id")
    if not token or not company_id:
        await ws.send_json({"error": "token e company_id obrigatórios"})
        await ws.close()
        return
    try:
        company_id = int(company_id)
    except ValueError:
        await ws.send_json({"error": "company_id inválido"})
        await ws.close()
        return
    user = _verify_ws_token(token, company_id)
    if not user:
        await ws.send_json({"error": "Não autorizado"})
        await ws.close()
        return
    with Session(engine) as session:
        server = session.get(Server, server_id)
        if not server or server.company_id != company_id:
            await ws.send_json({"error": "Servidor não encontrado"})
            await ws.close()
            return
        if not server.ssh_host or not server.ssh_user:
            await ws.send_json({"error": "Servidor sem SSH configurado"})
            await ws.close()
            return

    in_queue = queue.Queue()
    out_queue = queue.Queue()
    closed = threading.Event()
    loop = asyncio.get_event_loop()
    output_queue = asyncio.Queue()

    def forward_output():
        while True:
            try:
                data = out_queue.get()
                if data is None:
                    loop.call_soon_threadsafe(output_queue.put_nowait, None)
                    return
                loop.call_soon_threadsafe(output_queue.put_nowait, data)
            except Exception:
                return

    bridge_thread = threading.Thread(target=run_ssh_bridge, args=(server, out_queue, in_queue, closed))
    fwd_thread = threading.Thread(target=forward_output)
    bridge_thread.start()
    fwd_thread.start()

    async def send_output():
        while True:
            data = await output_queue.get()
            if data is None:
                break
            try:
                await ws.send_text(data)
            except Exception:
                break

    async def receive_input():
        try:
            while True:
                msg = await ws.receive_text()
                try:
                    obj = __import__("json").loads(msg)
                    if obj.get("type") == "input":
                        in_queue.put(obj.get("data", ""))
                except (ValueError, TypeError):
                    in_queue.put(msg)
        except WebSocketDisconnect:
            closed.set()

    try:
        await asyncio.gather(send_output(), receive_input())
    except WebSocketDisconnect:
        closed.set()
    finally:
        closed.set()
        in_queue.put(None)
        bridge_thread.join(timeout=3)
        fwd_thread.join(timeout=1)
