"""Agent CRUD routes."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from agentforge.db.base import get_db
from agentforge.db.models import Agent, User
from agentforge.auth.deps import get_current_user

router = APIRouter()

class AgentCreate(BaseModel):
    name: str
    role: str
    framework: str = 'native'
    system_prompt: str | None = None
    model: str = 'gpt-4o'
    skills: list[str] = []
    config: dict = {}

@router.get('')
async def list_agents(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.owner_id == user.id))
    agents = result.scalars().all()
    return [{'id': str(a.id), 'name': a.name, 'role': a.role, 'framework': a.framework,
              'model': a.model, 'skills': a.skills, 'is_active': a.is_active} for a in agents]

@router.post('', status_code=201)
async def create_agent(body: AgentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent = Agent(owner_id=user.id, **body.model_dump())
    db.add(agent)
    await db.commit()
    return {'id': str(agent.id), 'name': agent.name, 'role': agent.role}

@router.get('/{agent_id}')
async def get_agent(agent_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent or agent.owner_id != user.id: raise HTTPException(404, 'Agent not found')
    return {'id': str(agent.id), 'name': agent.name, 'role': agent.role, 'framework': agent.framework,
            'model': agent.model, 'skills': agent.skills, 'config': agent.config}

@router.delete('/{agent_id}', status_code=204)
async def delete_agent(agent_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent or agent.owner_id != user.id: raise HTTPException(404, 'Agent not found')
    await db.delete(agent)
    await db.commit()
