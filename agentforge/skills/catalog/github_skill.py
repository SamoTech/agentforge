"""Skill: github — interact with GitHub repos, issues, PRs via REST API."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class GitHubSkill(BaseSkill):
    name = "github"
    description = "Read/write GitHub repos, issues, pull requests, and files via REST API."
    category = "tool_use"
    tags = ["github", "git", "repo", "pr", "issue", "code", "ci"]
    level = "intermediate"
    requires_network = True
    input_schema = {
        "action":     {"type": "string", "required": True,
                       "description": "list_repos | get_repo | list_issues | create_issue | get_file | create_pr | list_prs"},
        "owner":      {"type": "string", "required": False},
        "repo":       {"type": "string", "required": False},
        "token":      {"type": "string", "required": False, "description": "GitHub PAT (falls back to env GITHUB_TOKEN)"},
        "params":     {"type": "object", "required": False, "description": "Action-specific params"},
    }
    output_schema = {"result": {"type": "any"}}

    _BASE = "https://api.github.com"

    async def execute(self, inp: SkillInput) -> SkillOutput:
        import os, httpx
        action = inp.data.get("action", "")
        owner  = inp.data.get("owner", "")
        repo   = inp.data.get("repo", "")
        token  = inp.data.get("token") or os.getenv("GITHUB_TOKEN", "")
        params = inp.data.get("params", {})
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async def _get(path, qp=None):
            async with httpx.AsyncClient(headers=headers, timeout=15) as c:
                r = await c.get(f"{self._BASE}{path}", params=qp)
                r.raise_for_status()
                return r.json()

        async def _post(path, body):
            async with httpx.AsyncClient(headers=headers, timeout=15) as c:
                r = await c.post(f"{self._BASE}{path}", json=body)
                r.raise_for_status()
                return r.json()

        try:
            if action == "list_repos":
                result = await _get(f"/users/{owner}/repos", {"per_page": params.get("per_page", 30)})
                return SkillOutput(data={"result": [{"name": r["name"], "description": r["description"], "stars": r["stargazers_count"]} for r in result]})

            elif action == "get_repo":
                result = await _get(f"/repos/{owner}/{repo}")
                return SkillOutput(data={"result": result})

            elif action == "list_issues":
                result = await _get(f"/repos/{owner}/{repo}/issues", {"state": params.get("state", "open"), "per_page": 30})
                return SkillOutput(data={"result": [{"number": i["number"], "title": i["title"], "state": i["state"]} for i in result]})

            elif action == "create_issue":
                result = await _post(f"/repos/{owner}/{repo}/issues", {"title": params["title"], "body": params.get("body", "")})
                return SkillOutput(data={"result": {"number": result["number"], "url": result["html_url"]}})

            elif action == "get_file":
                import base64
                result = await _get(f"/repos/{owner}/{repo}/contents/{params['path']}")
                content = base64.b64decode(result["content"]).decode()
                return SkillOutput(data={"result": {"content": content, "sha": result["sha"]}})

            elif action == "list_prs":
                result = await _get(f"/repos/{owner}/{repo}/pulls", {"state": params.get("state", "open")})
                return SkillOutput(data={"result": [{"number": p["number"], "title": p["title"], "state": p["state"]} for p in result]})

            else:
                return SkillOutput.fail(f"Unknown action: {action}")
        except Exception as e:
            return SkillOutput.fail(str(e))
