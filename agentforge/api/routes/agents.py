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

# Allowed roles and frameworks (validated on create + update)
_VALID_ROLES = {"planner", "executor", "specialist", "memory"}
_VALID_FRAMEWORKS = {"native", "langchain", "autogen", "crewai", "llama_index"}


class AgentCreate(BaseModel):
    name: str
    role: str = "executor"
    framework: str = "native"
    system_prompt: Optional[str] = None
    model: str = "gpt-4o"
    skills: list[str] = []
    config: dict = {}


class AgentUpdate(BaseModel):
    """Typed partial update — only these fields may be changed by the owner.
    Immutable fields (id, owner_id, created_at) are intentionally excluded.
    """
    name: Optional[str] = None
    role: Optional[str] = None
    framework: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    skills: Optional[list[str]] = None
    config: Optional[dict] = None
    is_active: Optional[bool] = None


class AgentOut(BaseModel):
    id: str
    name: str
    role: str
    framework: str
    model: str
    skills: list[str]
    is_active: bool


def _agent_out(a: Agent) -> AgentOut:
    return AgentOut(
        id=str(a.id), name=a.name, role=a.role, framework=a.framework,
        model=a.model, skills=a.skills or [], is_active=a.is_active,
    )


@router.get("/", response_model=list[AgentOut])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (await db.execute(select(Agent).where(Agent.owner_id == user.id))).scalars().all()
    return [_agent_out(a) for a in rows]


@router.post("/", response_model=AgentOut, status_code=201)
async def create_agent(
    body: AgentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.role not in _VALID_ROLES:
        raise HTTPException(422, f"role must be one of: {sorted(_VALID_ROLES)}")
    if body.framework not in _VALID_FRAMEWORKS:
        raise HTTPException(422, f"framework must be one of: {sorted(_VALID_FRAMEWORKS)}")
    agent = Agent(owner_id=user.id, **body.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _agent_out(agent)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,          # typed — immutable fields cannot be passed
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    agent = await db.get(Agent, agent_id)
    if not agent or agent.owner_id != user.id:
        raise HTTPException(404, "Agent not found")

    updates = body.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"] not in _VALID_ROLES:
        raise HTTPException(422, f"role must be one of: {sorted(_VALID_ROLES)}")
    if "framework" in updates and updates["framework"] not in _VALID_FRAMEWORKS:
        raise HTTPException(422, f"framework must be one of: {sorted(_VALID_FRAMEWORKS)}")

    for k, v in updates.items():
        setattr(agent, k, v)

    await db.commit()
    await db.refresh(agent)
    return _agent_out(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    agent = await db.get(Agent, agent_id)
    if not agent or agent.owner_id != user.id:
        raise HTTPException(404, "Agent not found")
    await db.delete(agent)
    await db.commit()
