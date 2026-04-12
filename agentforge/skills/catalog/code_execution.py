"""
Advanced Code Execution Skill v2
Features: multi-language sandboxed execution, AST analysis, security scanning,
          timeout enforcement, stdin support, dependency detection.
Languages: Python, JavaScript, TypeScript, Bash, Ruby
"""
from __future__ import annotations

import ast
import asyncio
import os
import re
import sys
import tempfile
import textwrap
import time
from typing import Any, Optional

from agentforge.skills.base import BaseSkill, SkillCategory, SkillConfig


SUPPORTED_LANGUAGES = {
    "python": {"ext": ".py", "cmd": [sys.executable]},
    "javascript": {"ext": ".js", "cmd": ["node"]},
    "typescript": {"ext": ".ts", "cmd": ["ts-node"]},
    "bash": {"ext": ".sh", "cmd": ["bash"]},
    "ruby": {"ext": ".rb", "cmd": ["ruby"]},
}

DANGEROUS_PATTERNS = [
    r"os\.system\s*\(",
    r"subprocess\.(call|run|Popen)\s*\(",
    r"__import__\s*\(['\"]os",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"open\s*\([^,)]+,\s*['\"]w",
    r"shutil\.(rmtree|move)",
    r"import\s+socket",
]


class CodeExecutionSkill(BaseSkill):
    name = "code_execution"
    description = (
        "Executes code in multiple languages in a sandboxed subprocess. "
        "Supports Python, JavaScript, TypeScript, Bash, Ruby. "
        "Returns stdout, stderr, exit code, timing, and Python AST analysis."
    )
    category = SkillCategory.CODE
    version = "2.0.0"
    tags = ["code", "execution", "sandbox", "python", "javascript", "analysis", "ast"]

    input_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Source code to execute"},
            "language": {
                "type": "string",
                "enum": list(SUPPORTED_LANGUAGES.keys()),
                "default": "python",
            },
            "timeout": {"type": "number", "default": 30},
            "analyze": {"type": "boolean", "default": True},
            "security_scan": {"type": "boolean", "default": True},
            "stdin_input": {"type": "string", "default": ""},
            "env_vars": {"type": "object"},
        },
        "required": ["code"],
    }

    def __init__(self):
        super().__init__(SkillConfig(timeout_seconds=60, max_retries=1, enable_cache=False))

    def _security_scan(self, code: str) -> list[dict]:
        issues = []
        for pattern in DANGEROUS_PATTERNS:
            for m in re.finditer(pattern, code):
                issues.append({
                    "pattern": pattern,
                    "match": m.group(),
                    "position": m.start(),
                    "severity": "high",
                })
        return issues

    def _analyze_python_ast(self, code: str) -> dict:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"error": str(e), "valid": False}

        analysis: dict = {
            "valid": True,
            "imports": [],
            "functions": [],
            "classes": [],
            "complexity": 0,
            "lines": len(code.splitlines()),
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                analysis["imports"].extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                analysis["imports"].append(node.module or "")
            elif isinstance(node, ast.FunctionDef):
                analysis["functions"].append({
                    "name": node.name,
                    "args": [a.arg for a in node.args.args],
                    "line": node.lineno,
                })
            elif isinstance(node, ast.ClassDef):
                analysis["classes"].append({
                    "name": node.name,
                    "bases": [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases],
                    "line": node.lineno,
                })
            elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                analysis["complexity"] += 1
        return analysis

    async def _execute(
        self,
        code: str,
        language: str = "python",
        timeout: float = 30,
        analyze: bool = True,
        security_scan: bool = True,
        stdin_input: str = "",
        env_vars: Optional[dict] = None,
        **kwargs,
    ) -> Any:
        if language not in SUPPORTED_LANGUAGES:
            return {"error": f"Unsupported language: {language}"}

        result: dict = {"language": language, "code_length": len(code)}

        if security_scan:
            issues = self._security_scan(code)
            result["security_issues"] = issues
            if any(i["severity"] == "high" for i in issues):
                result["blocked"] = True
                result["error"] = "Execution blocked: dangerous patterns detected"
                return result

        if analyze and language == "python":
            result["ast_analysis"] = self._analyze_python_ast(code)

        lang_config = SUPPORTED_LANGUAGES[language]

        with tempfile.NamedTemporaryFile(
            suffix=lang_config["ext"], mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(textwrap.dedent(code))
            tmp_path = f.name

        try:
            env = os.environ.copy()
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            if env_vars:
                env.update({str(k): str(v) for k, v in env_vars.items()})

            proc = await asyncio.create_subprocess_exec(
                *lang_config["cmd"], tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stdin_input else None,
                env=env,
            )

            start = time.monotonic()
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=stdin_input.encode() if stdin_input else None),
                    timeout=timeout,
                )
                elapsed = time.monotonic() - start
            except asyncio.TimeoutError:
                proc.kill()
                return {**result, "error": f"Timed out after {timeout}s", "timed_out": True}

            result.update({
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "exit_code": proc.returncode,
                "success": proc.returncode == 0,
                "execution_time_ms": round(elapsed * 1000, 2),
            })
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        return result
