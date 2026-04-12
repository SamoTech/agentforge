"""Skill: code_gen — generate, review, and refactor code in any language."""
from __future__ import annotations
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class CodeGenSkill(BaseSkill):
    name = "code_gen"
    description = (
        "Generate, review, refactor, or explain production-quality code in any language. "
        "Supports multi-file context, style guides, unit test generation, and docstring generation."
    )
    category = "code"
    tags = ["codegen", "programming", "llm", "generate", "refactor", "review", "tests"]
    level = "advanced"
    requires_llm = True
    input_schema = {
        "spec":       {"type": "string",  "required": True,  "description": "What to build / task description"},
        "language":   {"type": "string",  "default": "python","description": "Target programming language"},
        "mode":       {"type": "string",  "default": "generate",
                       "description": "generate | review | refactor | explain | tests | docstrings"},
        "style":      {"type": "string",  "default": "",      "description": "async | sync | class | function | module"},
        "context":    {"type": "string",  "default": "",      "description": "Existing code or codebase context"},
        "model":      {"type": "string",  "default": "gpt-4o","description": "LLM model override"},
        "temperature":{"type": "number",  "default": 0.15,    "description": "LLM sampling temperature"},
        "max_tokens": {"type": "integer", "default": 4096,    "description": "Max tokens in response"},
    }
    output_schema = {
        "code":        {"type": "string", "description": "Generated / transformed source code"},
        "language":    {"type": "string"},
        "explanation": {"type": "string", "description": "Optional explanation from LLM"},
        "tokens_used": {"type": "integer"},
    }

    _MODE_INSTRUCTIONS: dict[str, str] = {
        "generate":  (
            "You are a senior software engineer. Generate clean, production-ready, fully-implemented code. "
            "No placeholder comments like '# TODO' or '# implement here'. "
            "Include type hints, docstrings, and proper error handling. "
            "Return ONLY the code — no markdown fences, no explanations outside code comments."
        ),
        "review": (
            "You are a code reviewer. Analyse the provided code and return a structured review with sections: "
            "BUGS, SECURITY, PERFORMANCE, STYLE, and SUGGESTIONS. Be specific and actionable."
        ),
        "refactor": (
            "You are an expert at code refactoring. Rewrite the provided code to be cleaner, more idiomatic, "
            "and efficient while preserving all behaviour. Return ONLY the refactored code."
        ),
        "explain": (
            "You are a code explainer. Provide a clear, structured explanation of the provided code: "
            "what it does, how it works, and any noteworthy patterns or concerns."
        ),
        "tests": (
            "You are a senior QA engineer. Generate comprehensive unit tests for the provided code using pytest. "
            "Cover happy paths, edge cases, and error cases. Mock external dependencies. "
            "Return ONLY the test file code."
        ),
        "docstrings": (
            "Add or improve docstrings to all public classes, methods, and functions in the provided code. "
            "Use Google-style docstrings. Return ONLY the full updated code."
        ),
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        spec        = inp.data.get("spec", "").strip()
        lang        = inp.data.get("language", "python")
        mode        = inp.data.get("mode", "generate")
        style       = inp.data.get("style", "")
        context     = inp.data.get("context", "")
        model       = inp.data.get("model", "gpt-4o")
        temperature = float(inp.data.get("temperature", 0.15))
        max_tokens  = int(inp.data.get("max_tokens", 4096))

        if not spec:
            return SkillOutput.fail("spec is required")
        if mode not in self._MODE_INSTRUCTIONS:
            return SkillOutput.fail(f"mode must be one of: {list(self._MODE_INSTRUCTIONS)}")

        system_prompt = self._MODE_INSTRUCTIONS[mode]

        user_parts = [f"Language: {lang}"]
        if style:
            user_parts.append(f"Style: {style}")
        user_parts.append(f"\n{spec}")
        if context:
            user_parts.append(f"\n\n--- Existing code / context ---\n{context}")
        user_prompt = "\n".join(user_parts)

        try:
            from openai import AsyncOpenAI
            from agentforge.core.config import settings
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw = resp.choices[0].message.content or ""
            # Strip accidental markdown fences if model adds them
            code = raw.strip()
            if code.startswith("```"):
                lines = code.split("\n")
                code = "\n".join(
                    lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                )
            explanation = ""
            if mode in ("review", "explain"):
                explanation, code = code, ""

            return SkillOutput(
                data={"code": code, "language": lang, "explanation": explanation},
                tokens_used=resp.usage.total_tokens,
            )
        except Exception as e:
            return SkillOutput.fail(str(e))
