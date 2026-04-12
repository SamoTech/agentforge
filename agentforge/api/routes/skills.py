"""Skill discovery, search, and auto-generation routes."""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class SearchReq(BaseModel):
    query: str
    category: Optional[str] = None
    limit: int = 20


@router.get("/")
async def list_skills(request: Request, category: Optional[str] = None, tag: Optional[str] = None):
    reg = request.app.state.skill_registry
    if category:
        skills = reg.list_category(category)
    elif tag:
        skills = reg.list_tags(tag)
    else:
        skills = reg.list_all()
    return [s.meta() for s in skills]


@router.post("/search")
async def search_skills(body: SearchReq, request: Request):
    reg = request.app.state.skill_registry
    results = reg.search(body.query, limit=body.limit)
    if body.category:
        results = [s for s in results if s.category == body.category]
    return [s.meta() for s in results]


@router.get("/categories")
async def list_categories(request: Request):
    reg = request.app.state.skill_registry
    cats: dict[str, int] = {}
    for s in reg:
        cats[s.category] = cats.get(s.category, 0) + 1
    return [{"category": k, "count": v} for k, v in sorted(cats.items())]


@router.get("/{skill_name}")
async def get_skill(skill_name: str, request: Request):
    skill = request.app.state.skill_registry.get(skill_name)
    if not skill:
        raise HTTPException(404, f'Skill "{skill_name}" not found')
    return skill.meta()


@router.post("/generate")
async def generate_skill(body: dict, request: Request):
    """Auto-generate a skill from a natural language description."""
    reg = request.app.state.skill_registry
    generator = reg.get("auto_skill_generator")
    if not generator:
        raise HTTPException(503, "Auto-skill generator unavailable")
    from agentforge.skills.base import SkillInput
    out = await generator.execute(SkillInput(data=body))
    if not out.success:
        raise HTTPException(500, out.error)
    return out.data
