"""Auto-load all built-in skills into a registry."""
from __future__ import annotations
from agentforge.skills.registry.registry import SkillRegistry
from agentforge.skills.catalog.code_executor import CodeExecutorSkill
from agentforge.skills.catalog.http_request import HttpRequestSkill
from agentforge.skills.catalog.file_reader import FileReaderSkill
from agentforge.skills.catalog.summarizer import SummarizerSkill
from agentforge.skills.catalog.email_sender import EmailSenderSkill
from agentforge.skills.catalog.image_analyzer import ImageAnalyzerSkill
from agentforge.skills.catalog.db_query import DbQuerySkill
from agentforge.skills.catalog.llm_generate import LLMGenerateSkill
from agentforge.skills.catalog.web_search import WebSearchSkill
from agentforge.skills.catalog.auto_skill_generator import AutoSkillGeneratorSkill

BUILTIN_SKILLS = [
    CodeExecutorSkill,
    HttpRequestSkill,
    FileReaderSkill,
    SummarizerSkill,
    EmailSenderSkill,
    ImageAnalyzerSkill,
    DbQuerySkill,
    LLMGenerateSkill,
    WebSearchSkill,
    AutoSkillGeneratorSkill,
]


def load_all_skills(registry: SkillRegistry) -> None:
    """Register all built-in skills into the provided registry."""
    for skill_cls in BUILTIN_SKILLS:
        registry.register(skill_cls())
