"""Skills discovery routes."""
from fastapi import APIRouter
from agentforge.skills import registry

router = APIRouter()

@router.get('')
async def list_skills():
    """List all registered skills."""
    return [{'name': name, 'description': cls.description, 'category': cls.category, 'version': cls.version}
            for name, cls in registry.all_skills().items()]

@router.get('/categories')
async def list_categories():
    return registry.categories()

@router.get('/{skill_name}')
async def get_skill(skill_name: str):
    cls = registry.get(skill_name)
    if not cls: return {'error': f'Skill "{skill_name}" not found'}
    return {'name': cls.name, 'description': cls.description, 'category': cls.category, 'version': cls.version}
