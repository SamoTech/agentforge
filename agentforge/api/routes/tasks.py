"""Task submission, polling, and streaming routes."""
import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from agentforge.db.base import get_db
from agentforge.db.models import Task, User
from agentforge.auth.deps import get_current_user
from agentforge.core.logger import logger

router = APIRouter()

# Maximum seconds an orchestrator run may take before being force-failed
TASK_TIMEOUT_SECONDS = 300


class TaskCreate(BaseModel):
    title: str
    input: str
    agent_id: Optional[str] = None
    skills: list[str] = []


class TaskOut(BaseModel):
    id: str
    title: str
    status: str
    output: Optional[str]
    skills_used: list[str]
    token_usage: int
    cost_usd: float
    created_at: str


async def _run(task_id: str, user_input: str) -> None:
    """Background task that runs the orchestrator with a hard timeout."""
    from agentforge.db.base import AsyncSessionLocal
    from agentforge.orchestrator.orchestrator import Orchestrator

    async with AsyncSessionLocal() as db:
        task = await db.get(Task, uuid.UUID(task_id))
        if not task:
            return

        task.status = "running"
        await db.commit()

        try:
            result = await asyncio.wait_for(
                Orchestrator().run(user_input),
                timeout=TASK_TIMEOUT_SECONDS,
            )
            task.output       = result.output
            task.skills_used  = result.skills_used
            task.token_usage  = result.token_usage
            task.cost_usd     = result.cost_usd
            task.status       = "done"
            task.completed_at = datetime.utcnow()
        except asyncio.TimeoutError:
            task.status = "failed"
            task.output = f"Task timed out after {TASK_TIMEOUT_SECONDS}s"
            logger.error("task_timeout", task_id=task_id)
        except Exception as e:
            task.status = "failed"
            task.output = str(e)
            logger.error("task_error", task_id=task_id, error=str(e))

        await db.commit()


@router.post("/", response_model=TaskOut, status_code=201)
async def create_task(
    body: TaskCreate,
    bg: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t = Task(
        owner_id=user.id,
        agent_id=uuid.UUID(body.agent_id) if body.agent_id else None,
        title=body.title,
        input=body.input,
        status="pending",
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    bg.add_task(_run, str(t.id), body.input)
    return _task_out(t)


@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 50,
):
    rows = (
        await db.execute(
            select(Task).where(Task.owner_id == user.id)
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [_task_out(t) for t in rows]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    t = await db.get(Task, task_id)
    if not t or t.owner_id != user.id:
        raise HTTPException(404, "Task not found")
    return _task_out(t)


def _task_out(t: Task) -> TaskOut:
    return TaskOut(
        id=str(t.id), title=t.title, status=t.status, output=t.output,
        skills_used=t.skills_used or [], token_usage=t.token_usage,
        cost_usd=t.cost_usd, created_at=t.created_at.isoformat(),
    )
