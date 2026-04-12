"""WebSocket route — real-time task streaming and agent chat."""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agentforge.core.logger import logger

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, ws: WebSocket, client_id: str):
        await ws.accept()
        self.active[client_id] = ws
        logger.info("ws_connect", client=client_id)

    def disconnect(self, client_id: str):
        self.active.pop(client_id, None)
        logger.info("ws_disconnect", client=client_id)

    async def send(self, client_id: str, data: dict):
        ws = self.active.get(client_id)
        if ws:
            await ws.send_text(json.dumps(data))

    async def broadcast(self, data: dict):
        for ws in list(self.active.values()):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/task/{task_id}")
async def task_stream(ws: WebSocket, task_id: str):
    """Stream task status updates to the client."""
    await manager.connect(ws, task_id)
    try:
        while True:
            # Poll task status from DB every second and stream updates
            from agentforge.db.base import AsyncSessionLocal
            from agentforge.db.models import Task
            import uuid
            async with AsyncSessionLocal() as db:
                task = await db.get(Task, uuid.UUID(task_id))
                if task:
                    await manager.send(task_id, {
                        "type": "task_update",
                        "task_id": task_id,
                        "status": task.status,
                        "output": task.output,
                    })
                    if task.status in ("done", "failed"):
                        break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(task_id)


@router.websocket("/chat/{session_id}")
async def agent_chat(ws: WebSocket, session_id: str):
    """Interactive multi-turn agent chat over WebSocket."""
    await manager.connect(ws, session_id)
    from agentforge.memory.short_term import ShortTermMemory
    from agentforge.orchestrator.orchestrator import Orchestrator
    memory = ShortTermMemory(session_id)
    orchestrator = Orchestrator()
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            user_input = msg.get("message", "")
            if not user_input:
                continue
            await memory.add_message("user", user_input)
            context = await memory.get_context_window(last_n=10)
            await manager.send(session_id, {"type": "thinking", "session_id": session_id})
            result = await orchestrator.run(user_input, context=context)
            await memory.add_message("assistant", result.output)
            await manager.send(session_id, {
                "type": "message",
                "role": "assistant",
                "content": result.output,
                "skills_used": result.skills_used,
                "tokens": result.token_usage,
            })
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(session_id)
