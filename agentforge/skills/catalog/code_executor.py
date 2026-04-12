"""Skill: code_executor — safely run Python code in a resource-limited subprocess sandbox."""
from __future__ import annotations
import asyncio
import textwrap
import tempfile
import os
import resource
import sys
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput

# Dangerous imports that should never run in the sandbox
_BLOCKED_IMPORTS = {
    "subprocess", "multiprocessing", "ctypes", "cffi",
    "socket", "http", "urllib", "httpx", "requests",
    "ftplib", "smtplib", "telnetlib",
}

# Max output size returned (prevents OOM from print spam)
_MAX_OUTPUT_BYTES = 64 * 1024  # 64 KB


class CodeExecutorSkill(BaseSkill):
    name = "code_executor"
    description = (
        "Execute Python code in an isolated subprocess sandbox with resource limits. "
        "Blocks network imports, limits CPU time, memory, and output size. "
        "Returns stdout, stderr, exit code, and execution time."
    )
    category = "code"
    tags = ["python", "execution", "sandbox", "repl", "secure"]
    level = "advanced"
    input_schema = {
        "code":       {"type": "string",  "required": True,  "description": "Python source code"},
        "timeout":    {"type": "integer", "default": 15,     "description": "Max execution seconds"},
        "max_memory_mb": {"type": "integer", "default": 256, "description": "Max RAM in MB"},
        "allow_network": {"type": "boolean", "default": False,
                          "description": "Allow network imports (socket, httpx, etc.)"},
        "stdin":      {"type": "string",  "default": "",     "description": "Optional stdin input"},
    }
    output_schema = {
        "stdout":      {"type": "string"},
        "stderr":      {"type": "string"},
        "exit_code":   {"type": "integer"},
        "timed_out":   {"type": "boolean"},
        "elapsed_sec": {"type": "number"},
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        import time
        code          = inp.data.get("code", "")
        timeout       = int(inp.data.get("timeout", 15))
        max_mem_mb    = int(inp.data.get("max_memory_mb", 256))
        allow_network = bool(inp.data.get("allow_network", False))
        stdin_data    = inp.data.get("stdin", "")

        if not code.strip():
            return SkillOutput.fail("No code provided")

        # Static import scan — block dangerous modules before even running
        if not allow_network:
            for mod in _BLOCKED_IMPORTS:
                if f"import {mod}" in code or f"from {mod}" in code:
                    return SkillOutput.fail(
                        f"Blocked: import of '{mod}' is not allowed in sandbox. "
                        "Set allow_network=true to enable network imports."
                    )

        # Write code to temp file
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(textwrap.dedent(code))
            tmp_path = f.name

        def _set_limits():
            """Called in subprocess after fork — applies resource limits."""
            # CPU time hard limit
            resource.setrlimit(resource.RLIMIT_CPU, (timeout + 2, timeout + 2))
            # Virtual memory limit
            mem_bytes = max_mem_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            # Prevent writing large files
            resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))

        start = time.monotonic()
        try:
            preexec = _set_limits if sys.platform != "win32" else None
            proc = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdin=asyncio.subprocess.PIPE if stdin_data else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=preexec,
                # Limit environment — strip API keys, tokens from child process
                env={k: v for k, v in os.environ.items()
                     if not any(s in k.upper() for s in
                                ["KEY", "SECRET", "TOKEN", "PASSWORD", "PASS"])},
            )
            stdin_bytes = stdin_data.encode() if stdin_data else None
            timed_out = False
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=stdin_bytes), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()  # drain
                timed_out = True
                stdout, stderr = b"", b"TimeoutError: execution exceeded limit"

            elapsed = time.monotonic() - start
            # Truncate large outputs
            stdout_s = stdout[:_MAX_OUTPUT_BYTES].decode(errors="replace")
            stderr_s = stderr[:_MAX_OUTPUT_BYTES].decode(errors="replace")

            return SkillOutput(
                success=proc.returncode == 0 and not timed_out,
                data={
                    "stdout":      stdout_s,
                    "stderr":      stderr_s,
                    "exit_code":   proc.returncode if not timed_out else -1,
                    "timed_out":   timed_out,
                    "elapsed_sec": round(elapsed, 3),
                },
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
