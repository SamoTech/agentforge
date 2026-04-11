"""Code generation skill — generate code in any language."""
from openai import AsyncOpenAI
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput
from agentforge.skills.registry import register
from agentforge.core.config import settings

@register
class CodeGeneratorSkill(BaseSkill):
    name = 'code_generator'
    description = 'Generate, refactor, or explain code in any programming language'
    category = 'code'

    async def execute(self, input: SkillInput) -> SkillOutput:
        prompt = input.data.get('prompt', '')
        language = input.data.get('language', 'python')
        task = input.data.get('task', 'generate')  # generate | refactor | explain | review
        if not prompt: return SkillOutput.fail('prompt is required')

        system_map = {
            'generate': f'You are an expert {language} developer. Write clean, production-ready code with error handling and docstrings. Return only the code block.',
            'refactor': f'You are a senior {language} engineer. Refactor the provided code for clarity, performance, and best practices. Return the improved code with a brief explanation.',
            'explain': 'You are a programming tutor. Explain the provided code clearly, covering what it does, how it works, and any important patterns used.',
            'review': f'You are a senior {language} code reviewer. Review the code for bugs, security issues, performance problems, and style. Provide specific, actionable feedback.',
        }
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_default_model,
            messages=[
                {'role': 'system', 'content': system_map.get(task, system_map['generate'])},
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.1,
        )
        return SkillOutput.ok({'code': response.choices[0].message.content, 'language': language, 'task': task})
