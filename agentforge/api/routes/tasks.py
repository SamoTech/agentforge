"""Task execution routes."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from agentforge.db.base import get_db
from agentforge.db.models import Task, Agent, User
from agentforge.auth.deps import get_current_user
from agentforge.orchestrator.orchestrator import Orchestrator

router = APIRouter()

class TaskCreate(BaseModel):
    title: str
    input: str
    agent_id: uuid.UUID | None = None

async def _run_task(task_id: uuid.UUID, input_text: str):
    """Background task execution."""
    from agentforge.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, task_id)
        if not task: return
        try:
            task.status = 'running'
            await db.commit()
            orchestrator = Orchestrator()
            result = await orchestrator.run(input_text)
            task.output = result.output
            task.status = 'completed'
            task.skills_used = result.skills_used
            task.token_usage = result.token_usage
            task.cost_usd = result.cost_usd
            task.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            task.status = 'failed'
            task.output = str(e)
        await db.commit()

@router.post('', status_code=202)
async def create_task(body: TaskCreate, background_tasks: BackgroundTasks,
                       user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = Task(owner_id=user.id, agent_id=body.agent_id, title=body.title, input=body.input)
    db.add(task)
    await db.commit()
    background_tasks.add_task(_run_task, task.id, body.input)
    return {'task_id': str(task.id), 'status': 'queued'}

@router.get('/{task_id}')
async def get_task(task_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task or task.owner_id != user.id: raise HTTPException(404, 'Task not found')
    return {'id': str(task.id), 'title': task.title, 'status': task.status,
            'input': task.input, 'output': task.output, 'skills_used': task.skills_used,
            'token_usage': task.token_usage, 'cost_usd': task.cost_usd,
            'created_at': task.created_at.isoformat(), 'completed_at': task.completed_at.isoformat() if task.completed_at else None}

@router.get('')
async def list_tasks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.owner_id == user.id).order_by(Task.created_at.desc()).limit(50))
    tasks = result.scalars().all()
    return [{'id': str(t.id), 'title': t.title, 'status': t.status, 'created_at': t.created_at.isoformat()} for t in tasks]
