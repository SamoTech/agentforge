"""Skill: http_request — HTTP client with retries, auth, streaming, and response parsing."""
from __future__ import annotations
import httpx
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class HttpRequestSkill(BaseSkill):
    name = "http_request"
    description = (
        "Make HTTP GET/POST/PUT/PATCH/DELETE requests with automatic retries, "
        "configurable auth (Bearer, Basic, API-Key), response parsing (JSON/text/binary), "
        "and optional response size limits."
    )
    category = "web"
    tags = ["http", "api", "rest", "webhook", "fetch", "retry", "auth"]
    level = "advanced"
    requires_network = True
    input_schema = {
        "url":          {"type": "string",  "required": True},
        "method":       {"type": "string",  "default": "GET",
                         "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]},
        "headers":      {"type": "object",  "default": {}},
        "body":         {"type": "any",     "default": None,
                         "description": "Request body (dict for JSON, string for raw)"},
        "params":       {"type": "object",  "default": {},
                         "description": "Query string parameters"},
        "timeout":      {"type": "integer", "default": 30},
        "retries":      {"type": "integer", "default": 3,
                         "description": "Max retry attempts on network errors (0 = no retry)"},
        "auth_type":    {"type": "string",  "default": "",
                         "description": "bearer | basic | api_key | none"},
        "auth_value":   {"type": "string",  "default": "",
                         "description": "Token / 'user:pass' / API key value"},
        "auth_header":  {"type": "string",  "default": "X-API-Key",
                         "description": "Header name when auth_type=api_key"},
        "follow_redirects": {"type": "boolean", "default": True},
        "max_response_kb": {"type": "integer", "default": 2048,
                            "description": "Truncate response body at this size in KB"},
        "verify_ssl":   {"type": "boolean", "default": True},
    }
    output_schema = {
        "status_code":    {"type": "integer"},
        "body":           {"type": "any"},
        "headers":        {"type": "object"},
        "elapsed_ms":     {"type": "integer"},
        "content_type":   {"type": "string"},
        "truncated":      {"type": "boolean"},
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        url           = inp.data.get("url", "")
        method        = inp.data.get("method", "GET").upper()
        headers       = dict(inp.data.get("headers", {}) or {})
        body          = inp.data.get("body", None)
        qparams       = inp.data.get("params", {}) or {}
        timeout       = int(inp.data.get("timeout", 30))
        max_retries   = int(inp.data.get("retries", 3))
        auth_type     = inp.data.get("auth_type", "").lower()
        auth_value    = inp.data.get("auth_value", "")
        auth_header   = inp.data.get("auth_header", "X-API-Key")
        follow_redir  = bool(inp.data.get("follow_redirects", True))
        max_resp_kb   = int(inp.data.get("max_response_kb", 2048))
        verify_ssl    = bool(inp.data.get("verify_ssl", True))

        if not url:
            return SkillOutput.fail("url is required")

        # ── Auth injection ────────────────────────────────────────────────
        if auth_type == "bearer":
            headers["Authorization"] = f"Bearer {auth_value}"
        elif auth_type == "basic":
            import base64
            encoded = base64.b64encode(auth_value.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        elif auth_type == "api_key":
            headers[auth_header] = auth_value

        # ── Request kwargs ────────────────────────────────────────────────
        req_kwargs: dict = {
            "headers":          headers,
            "params":           qparams,
            "follow_redirects": follow_redir,
            "verify":           verify_ssl,
        }
        if isinstance(body, dict):
            req_kwargs["json"] = body
        elif isinstance(body, str):
            req_kwargs["content"] = body.encode()

        # ── Retry loop ────────────────────────────────────────────────────
        from tenacity import (
            retry, stop_after_attempt, wait_exponential,
            retry_if_exception_type, RetryError,
        )
        import time

        attempts  = 0
        last_err  = None

        async def _do_request() -> httpx.Response:
            async with httpx.AsyncClient(timeout=timeout) as c:
                return await c.request(method, url, **req_kwargs)

        for attempt in range(max(1, max_retries)):
            try:
                start    = time.monotonic()
                response = await _do_request()
                elapsed  = int((time.monotonic() - start) * 1000)
                break
            except (httpx.TransportError, httpx.TimeoutException) as e:
                last_err = str(e)
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(min(0.5 * (2 ** attempt), 8))
                else:
                    return SkillOutput.fail(f"Request failed after {max_retries} attempts: {last_err}")

        # ── Parse response ────────────────────────────────────────────────
        content_type = response.headers.get("content-type", "")
        max_bytes    = max_resp_kb * 1024
        raw_bytes    = response.content[:max_bytes]
        truncated    = len(response.content) > max_bytes

        if "application/json" in content_type:
            try:
                import json
                parsed_body = json.loads(raw_bytes)
            except Exception:
                parsed_body = raw_bytes.decode(errors="replace")
        elif content_type.startswith("text/"):
            parsed_body = raw_bytes.decode(errors="replace")
        else:
            import base64
            parsed_body = base64.b64encode(raw_bytes).decode()  # binary as base64

        return SkillOutput(
            success=200 <= response.status_code < 300,
            data={
                "status_code":  response.status_code,
                "body":         parsed_body,
                "headers":      dict(response.headers),
                "elapsed_ms":   elapsed,
                "content_type": content_type,
                "truncated":    truncated,
            },
        )
