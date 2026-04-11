"""Skill discovery and auto-generation routes."""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


@router.get('/')
async def list_skills(request: Request, category: Optional[str] = None):
    registry = request.app.state.skill_registry
    skills = registry.list_all()
    if category:
        skills = [s for s in skills if s.category == category]
    return [{'name': s.name, 'description': s.description, 'category': s.category,
              'tags': s.tags, 'level': getattr(s, 'level', 'basic'),
              'input_schema': s.input_schema, 'output_schema': s.output_schema} for s in skills]


@router.post('/search')
async def search_skills(body: dict, request: Request):
    registry = request.app.state.skill_registry
    results = registry.search(body.get('query', ''), limit=body.get('limit', 20))
    return [{'name': s.name, 'description': s.description, 'category': s.category} for s in results]


@router.get('/{skill_name}')
async def get_skill(skill_name: str, request: Request):
    skill = request.app.state.skill_registry.get(skill_name)
    if not skill: raise HTTPException(404, f'Skill "{skill_name}" not found')
    return {'name': skill.name, 'description': skill.description, 'category': skill.category,
            'tags': skill.tags, 'input_schema': skill.input_schema, 'output_schema': skill.output_schema}


@router.post('/generate')
async def generate_skill(body: dict, request: Request):
    registry = request.app.state.skill_registry
    gen = registry.get('auto_skill_generator')
    if not gen: raise HTTPException(503, 'Auto-skill generator not available')
    from agentforge.skills.base import SkillInput
    result = await gen.execute(SkillInput(data={'description': body.get('description', '')}))
    if not result.success: raise HTTPException(500, result.error)
    return result.data
