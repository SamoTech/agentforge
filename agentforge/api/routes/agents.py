"""Agent CRUD routes."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from agentforge.db.base import get_db
from agentforge.db.models import Agent, User
from agentforge.auth.deps import get_current_user

router = APIRouter()


class AgentCreate(BaseModel):
    name: str; role: str = 'executor'; framework: str = 'native'
    system_prompt: Optional[str] = None; model: str = 'gpt-4o'
    skills: list[str] = []; config: dict = {}


@router.get('/')
async def list_agents(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    r = await db.execute(select(Agent).where(Agent.owner_id == user.id))
    return [{'id': str(a.id), 'name': a.name, 'role': a.role, 'framework': a.framework,
              'model': a.model, 'skills': a.skills or [], 'is_active': a.is_active}
            for a in r.scalars().all()]


@router.post('/', status_code=201)
async def create_agent(body: AgentCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    agent = Agent(owner_id=user.id, name=body.name, role=body.role, framework=body.framework,
                  system_prompt=body.system_prompt, model=body.model, skills=body.skills, config=body.config)
    db.add(agent); await db.commit(); await db.refresh(agent)
    return {'id': str(agent.id), 'name': agent.name, 'role': agent.role, 'framework': agent.framework,
            'model': agent.model, 'skills': agent.skills or [], 'is_active': agent.is_active}


@router.delete('/{agent_id}', status_code=204)
async def delete_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    agent = await db.get(Agent, agent_id)
    if not agent or agent.owner_id != user.id: raise HTTPException(404, 'Agent not found')
    await db.delete(agent); await db.commit()
