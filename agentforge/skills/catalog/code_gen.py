"""Skill: code_gen — generate code in any language from a natural language spec."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class CodeGenSkill(BaseSkill):
    name = "code_gen"
    description = "Generate production-quality code in any language from a natural language description."
    category = "code"
    tags = ["codegen", "programming", "llm", "generate", "python", "typescript"]
    level = "intermediate"
    requires_llm = True
    input_schema = {
        "spec":       {"type": "string", "required": True,  "description": "What to build"},
        "language":   {"type": "string", "required": False, "description": "Target language (default: python)"},
        "style":      {"type": "string", "required": False, "description": "async | sync | class | function"},
        "model":      {"type": "string", "required": False, "description": "LLM model override"},
        "context":    {"type": "string", "required": False, "description": "Extra context / existing code"},
    }
    output_schema = {
        "code":       {"type": "string", "description": "Generated source code"},
        "language":   {"type": "string"},
        "explanation":{"type": "string"},
    }

    _SYSTEM = (
        "You are an expert software engineer. Generate clean, production-ready code with no "
        "placeholder comments. Include docstrings and type hints where appropriate. "
        "Return ONLY the code block, no markdown fences."
    )

    async def execute(self, inp: SkillInput) -> SkillOutput:
        spec     = inp.data.get("spec", "")
        lang     = inp.data.get("language", "python")
        style    = inp.data.get("style", "")
        model    = inp.data.get("model", "gpt-4o")
        ctx      = inp.data.get("context", "")
        if not spec:
            return SkillOutput.fail("spec is required")
        prompt = f"Language: {lang}\nStyle: {style or 'auto'}\nSpec: {spec}"
        if ctx:
            prompt += f"\n\nExisting context:\n{ctx}"
        try:
            from openai import AsyncOpenAI
            from agentforge.core.config import settings
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.2,
            )
            code = resp.choices[0].message.content or ""
            return SkillOutput(
                data={"code": code, "language": lang, "explanation": ""},
                tokens_used=resp.usage.total_tokens,
            )
        except Exception as e:
            return SkillOutput.fail(str(e))
