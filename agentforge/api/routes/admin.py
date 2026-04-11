"""Admin-only routes for platform stats and management."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from agentforge.db.base import get_db
from agentforge.db.models import User, Agent, Task
from agentforge.auth.deps import get_current_admin

router = APIRouter()


@router.get('/stats')
async def platform_stats(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin)):
    return {
        'users':        await db.scalar(select(func.count()).select_from(User)),
        'agents':       await db.scalar(select(func.count()).select_from(Agent)),
        'tasks_total':  await db.scalar(select(func.count()).select_from(Task)),
        'tasks_done':   await db.scalar(select(func.count()).select_from(Task).where(Task.status == 'done')),
        'tokens_total': await db.scalar(select(func.sum(Task.token_usage)).select_from(Task)) or 0,
        'cost_usd':     round(float(await db.scalar(select(func.sum(Task.cost_usd)).select_from(Task)) or 0), 4),
    }


@router.get('/users')
async def list_users(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_admin), limit: int = 100):
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(limit))
    return [{'id': str(u.id), 'email': u.email, 'plan': u.plan, 'is_active': u.is_active,
              'created_at': u.created_at.isoformat()} for u in result.scalars().all()]
