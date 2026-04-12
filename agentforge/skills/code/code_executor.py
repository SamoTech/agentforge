"""Sandboxed Python code execution skill."""
import ast
import io
import traceback
from typing import Any
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput
from agentforge.skills.registry import register

# Blocked builtins for safety
_BLOCKED = {'__import__', 'eval', 'exec', 'compile', 'open', '__builtins__'}

def _safe_exec(code: str, timeout: int = 10) -> tuple[str, str, dict]:
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    local_vars: dict[str, Any] = {}
    try:
        tree = ast.parse(code)
        # Simple AST safety check
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, 'id', getattr(func, 'attr', ''))
                if name in _BLOCKED:
                    raise ValueError(f'Blocked operation: {name}')
        import contextlib
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            exec(compile(tree, '<sandbox>', 'exec'), {'__builtins__': {}}, local_vars)
        return stdout_capture.getvalue(), '', local_vars
    except Exception:
        return stdout_capture.getvalue(), traceback.format_exc(), {}

@register
class CodeExecutorSkill(BaseSkill):
    name = 'code_executor'
    description = 'Execute Python code in a sandboxed environment and return output'
    category = 'code'

    async def execute(self, input: SkillInput) -> SkillOutput:
        code = input.data.get('code', '')
        if not code:
            return SkillOutput.fail('code is required')
        stdout, stderr, variables = _safe_exec(code)
        return SkillOutput.ok({'stdout': stdout, 'stderr': stderr, 'variables': {k: str(v) for k, v in variables.items()}})
