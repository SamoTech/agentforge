"""WebSocket route for real-time agent streaming."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agentforge.orchestrator.orchestrator import Orchestrator
from agentforge.core.logger import logger
import json

router = APIRouter()

@router.websocket('/run')
async def websocket_run(websocket: WebSocket):
    await websocket.accept()
    logger.info('WebSocket connected')
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                task = data.get('task', '')
                if not task:
                    await websocket.send_json({'type': 'error', 'message': 'task field required'})
                    continue
                await websocket.send_json({'type': 'status', 'status': 'planning'})
                orchestrator = Orchestrator()
                result = await orchestrator.run(task)
                await websocket.send_json({
                    'type': 'result',
                    'output': result.output,
                    'skills_used': result.skills_used,
                    'token_usage': result.token_usage,
                    'cost_usd': result.cost_usd,
                })
            except Exception as e:
                await websocket.send_json({'type': 'error', 'message': str(e)})
    except WebSocketDisconnect:
        logger.info('WebSocket disconnected')
