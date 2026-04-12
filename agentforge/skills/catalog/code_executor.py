"""Skill: code_executor — run Python code in a sandboxed subprocess."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class CodeExecutorSkill(BaseSkill):
    name = "code_executor"
    description = "Execute Python code in an isolated subprocess and return stdout/stderr."
    category = "code"
    tags = ["execute", "run", "python", "sandbox", "subprocess"]
    level = "advanced"
    stability = "experimental"
    input_schema = {
        "code":       {"type": "string",  "required": True,  "description": "Python code to execute"},
        "timeout":    {"type": "integer", "required": False, "description": "Max seconds (default 10)"},
        "stdin":      {"type": "string",  "required": False, "description": "Optional stdin input"},
    }
    output_schema = {
        "stdout":      {"type": "string"},
        "stderr":      {"type": "string"},
        "returncode":  {"type": "integer"},
        "timed_out":   {"type": "boolean"},
    }

    # Blocked modules for basic sandboxing
    _BLOCKED = ["os.system", "subprocess", "shutil.rmtree", "eval(", "exec("]

    async def execute(self, inp: SkillInput) -> SkillOutput:
        code    = inp.data.get("code", "")
        timeout = int(inp.data.get("timeout", 10))
        stdin   = inp.data.get("stdin", None)
        if not code:
            return SkillOutput.fail("code is required")
        for blocked in self._BLOCKED:
            if blocked in code:
                return SkillOutput.fail(f"Blocked construct: {blocked}")
        try:
            import asyncio
            proc = await asyncio.create_subprocess_exec(
                "python3", "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stdin else None,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(input=stdin.encode() if stdin else None),
                    timeout=timeout,
                )
                timed_out = False
            except asyncio.TimeoutError:
                proc.kill()
                stdout_b, stderr_b = b"", b"TimeoutError: execution exceeded limit"
                timed_out = True
            return SkillOutput(data={
                "stdout":     stdout_b.decode(errors="replace"),
                "stderr":     stderr_b.decode(errors="replace"),
                "returncode": proc.returncode or 0,
                "timed_out":  timed_out,
            })
        except Exception as e:
            return SkillOutput.fail(str(e))
