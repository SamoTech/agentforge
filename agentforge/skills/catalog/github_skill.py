"""Skill: github — full GitHub REST API integration."""
from __future__ import annotations
import os
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class GitHubSkill(BaseSkill):
    name = "github"
    description = (
        "Full GitHub integration: repos, issues, PRs, files, branches, commits, "
        "releases, code search, and webhooks via REST API v3."
    )
    category = "tool_use"
    tags = ["github", "git", "repo", "pr", "issue", "code", "ci", "release", "branch"]
    level = "advanced"
    requires_network = True
    input_schema = {
        "action": {
            "type": "string", "required": True,
            "description": (
                "list_repos | get_repo | list_issues | create_issue | close_issue | "
                "get_file | create_file | update_file | delete_file | "
                "list_prs | create_pr | merge_pr | get_pr | "
                "list_branches | create_branch | "
                "list_commits | get_commit | "
                "list_releases | create_release | "
                "search_code | search_repos | "
                "add_comment | list_comments | "
                "get_user | list_collaborators"
            ),
        },
        "owner":  {"type": "string", "required": False},
        "repo":   {"type": "string", "required": False},
        "token":  {"type": "string", "required": False, "description": "PAT (falls back to GITHUB_TOKEN env)"},
        "params": {"type": "object", "required": False, "description": "Action-specific parameters"},
    }
    output_schema = {"result": {"type": "any"}, "pagination": {"type": "object"}}

    _BASE = "https://api.github.com"

    async def execute(self, inp: SkillInput) -> SkillOutput:
        action = inp.data.get("action", "").strip()
        owner  = inp.data.get("owner", "")
        repo   = inp.data.get("repo", "")
        token  = inp.data.get("token") or os.getenv("GITHUB_TOKEN", "")
        params = inp.data.get("params", {}) or {}

        if not action:
            return SkillOutput.fail("action is required")

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            import httpx

            async def _get(path: str, qp: dict | None = None) -> dict | list:
                async with httpx.AsyncClient(headers=headers, timeout=20) as c:
                    r = await c.get(f"{self._BASE}{path}", params=qp or {})
                    r.raise_for_status()
                    return r.json()

            async def _post(path: str, body: dict) -> dict:
                async with httpx.AsyncClient(headers=headers, timeout=20) as c:
                    r = await c.post(f"{self._BASE}{path}", json=body)
                    r.raise_for_status()
                    return r.json()

            async def _patch(path: str, body: dict) -> dict:
                async with httpx.AsyncClient(headers=headers, timeout=20) as c:
                    r = await c.patch(f"{self._BASE}{path}", json=body)
                    r.raise_for_status()
                    return r.json()

            async def _put(path: str, body: dict) -> dict:
                async with httpx.AsyncClient(headers=headers, timeout=20) as c:
                    r = await c.put(f"{self._BASE}{path}", json=body)
                    r.raise_for_status()
                    return r.json()

            async def _delete(path: str, body: dict | None = None) -> dict | None:
                async with httpx.AsyncClient(headers=headers, timeout=20) as c:
                    r = await c.request("DELETE", f"{self._BASE}{path}", json=body)
                    r.raise_for_status()
                    return r.json() if r.content else None

            # ── Repositories ─────────────────────────────────────────────
            if action == "list_repos":
                data = await _get(f"/users/{owner}/repos",
                                  {"per_page": params.get("per_page", 30), "sort": params.get("sort", "updated")})
                return SkillOutput(data={"result": [
                    {"name": r["name"], "description": r["description"],
                     "stars": r["stargazers_count"], "language": r["language"],
                     "url": r["html_url"], "private": r["private"]}
                    for r in data
                ]})

            if action == "get_repo":
                data = await _get(f"/repos/{owner}/{repo}")
                return SkillOutput(data={"result": data})

            if action == "search_repos":
                q = params.get("query", f"user:{owner}")
                data = await _get("/search/repositories",
                                  {"q": q, "per_page": params.get("per_page", 10)})
                return SkillOutput(data={"result": data.get("items", []),
                                         "pagination": {"total": data.get("total_count", 0)}})

            # ── Issues ───────────────────────────────────────────────────
            if action == "list_issues":
                data = await _get(f"/repos/{owner}/{repo}/issues",
                                  {"state": params.get("state", "open"),
                                   "labels": params.get("labels", ""),
                                   "per_page": params.get("per_page", 30)})
                return SkillOutput(data={"result": [
                    {"number": i["number"], "title": i["title"],
                     "state": i["state"], "labels": [l["name"] for l in i["labels"]],
                     "url": i["html_url"], "created_at": i["created_at"]}
                    for i in data if not i.get("pull_request")  # exclude PRs
                ]})

            if action == "create_issue":
                body: dict = {"title": params["title"], "body": params.get("body", "")}
                if params.get("labels"):
                    body["labels"] = params["labels"]
                if params.get("assignees"):
                    body["assignees"] = params["assignees"]
                data = await _post(f"/repos/{owner}/{repo}/issues", body)
                return SkillOutput(data={"result": {"number": data["number"], "url": data["html_url"]}})

            if action == "close_issue":
                data = await _patch(f"/repos/{owner}/{repo}/issues/{params['number']}",
                                    {"state": "closed"})
                return SkillOutput(data={"result": {"number": data["number"], "state": data["state"]}})

            if action == "add_comment":
                kind = params.get("kind", "issue")  # issue | pr
                num  = params["number"]
                data = await _post(f"/repos/{owner}/{repo}/issues/{num}/comments",
                                   {"body": params["comment"]})
                return SkillOutput(data={"result": {"id": data["id"], "url": data["html_url"]}})

            if action == "list_comments":
                data = await _get(f"/repos/{owner}/{repo}/issues/{params['number']}/comments")
                return SkillOutput(data={"result": [
                    {"id": c["id"], "user": c["user"]["login"],
                     "body": c["body"], "created_at": c["created_at"]}
                    for c in data
                ]})

            # ── Files ────────────────────────────────────────────────────
            if action == "get_file":
                import base64
                data = await _get(f"/repos/{owner}/{repo}/contents/{params['path']}",
                                  {"ref": params.get("ref", "")})
                if isinstance(data, list):
                    return SkillOutput(data={"result": [{"name": f["name"], "type": f["type"], "size": f["size"]} for f in data]})
                content = base64.b64decode(data["content"]).decode(errors="replace")
                return SkillOutput(data={"result": {"content": content, "sha": data["sha"], "size": data["size"]}})

            if action == "create_file":
                import base64
                b64 = base64.b64encode(params["content"].encode()).decode()
                data = await _put(f"/repos/{owner}/{repo}/contents/{params['path']}",
                                  {"message": params.get("message", "Create file via AgentForge"),
                                   "content": b64,
                                   "branch": params.get("branch", "main")})
                return SkillOutput(data={"result": {"path": data["content"]["path"], "sha": data["content"]["sha"]}})

            if action == "update_file":
                import base64
                b64 = base64.b64encode(params["content"].encode()).decode()
                data = await _put(f"/repos/{owner}/{repo}/contents/{params['path']}",
                                  {"message": params.get("message", "Update file via AgentForge"),
                                   "content": b64,
                                   "sha": params["sha"],
                                   "branch": params.get("branch", "main")})
                return SkillOutput(data={"result": {"path": data["content"]["path"]}})

            if action == "delete_file":
                data = await _delete(f"/repos/{owner}/{repo}/contents/{params['path']}",
                                     {"message": params.get("message", "Delete file via AgentForge"),
                                      "sha": params["sha"],
                                      "branch": params.get("branch", "main")})
                return SkillOutput(data={"result": {"deleted": True}})

            # ── Pull Requests ─────────────────────────────────────────────
            if action == "list_prs":
                data = await _get(f"/repos/{owner}/{repo}/pulls",
                                  {"state": params.get("state", "open"), "per_page": params.get("per_page", 20)})
                return SkillOutput(data={"result": [
                    {"number": p["number"], "title": p["title"], "state": p["state"],
                     "head": p["head"]["ref"], "base": p["base"]["ref"],
                     "url": p["html_url"], "draft": p["draft"]}
                    for p in data
                ]})

            if action == "get_pr":
                data = await _get(f"/repos/{owner}/{repo}/pulls/{params['number']}")
                return SkillOutput(data={"result": data})

            if action == "create_pr":
                data = await _post(f"/repos/{owner}/{repo}/pulls", {
                    "title": params["title"],
                    "body":  params.get("body", ""),
                    "head":  params["head"],
                    "base":  params.get("base", "main"),
                    "draft": params.get("draft", False),
                })
                return SkillOutput(data={"result": {"number": data["number"], "url": data["html_url"]}})

            if action == "merge_pr":
                data = await _put(f"/repos/{owner}/{repo}/pulls/{params['number']}/merge", {
                    "merge_method": params.get("method", "squash"),
                    "commit_title": params.get("title", ""),
                })
                return SkillOutput(data={"result": {"merged": data.get("merged", False), "sha": data.get("sha")}})

            # ── Branches ─────────────────────────────────────────────────
            if action == "list_branches":
                data = await _get(f"/repos/{owner}/{repo}/branches")
                return SkillOutput(data={"result": [{"name": b["name"], "sha": b["commit"]["sha"]} for b in data]})

            if action == "create_branch":
                # Get SHA of source branch first
                src = await _get(f"/repos/{owner}/{repo}/git/refs/heads/{params.get('from', 'main')}")
                sha = src["object"]["sha"]
                data = await _post(f"/repos/{owner}/{repo}/git/refs", {
                    "ref": f"refs/heads/{params['name']}",
                    "sha": sha,
                })
                return SkillOutput(data={"result": {"ref": data["ref"], "sha": data["object"]["sha"]}})

            # ── Commits ──────────────────────────────────────────────────
            if action == "list_commits":
                data = await _get(f"/repos/{owner}/{repo}/commits",
                                  {"per_page": params.get("per_page", 20),
                                   "sha": params.get("branch", ""),
                                   "author": params.get("author", "")})
                return SkillOutput(data={"result": [
                    {"sha": c["sha"][:7], "message": c["commit"]["message"].split("\n")[0],
                     "author": c["commit"]["author"]["name"], "date": c["commit"]["author"]["date"]}
                    for c in data
                ]})

            if action == "get_commit":
                data = await _get(f"/repos/{owner}/{repo}/commits/{params['sha']}")
                return SkillOutput(data={"result": {
                    "sha": data["sha"], "message": data["commit"]["message"],
                    "author": data["commit"]["author"]["name"],
                    "files_changed": len(data.get("files", [])),
                    "stats": data.get("stats", {}),
                }})

            # ── Releases ─────────────────────────────────────────────────
            if action == "list_releases":
                data = await _get(f"/repos/{owner}/{repo}/releases",
                                  {"per_page": params.get("per_page", 10)})
                return SkillOutput(data={"result": [
                    {"id": r["id"], "tag": r["tag_name"], "name": r["name"],
                     "draft": r["draft"], "prerelease": r["prerelease"],
                     "created_at": r["created_at"]}
                    for r in data
                ]})

            if action == "create_release":
                data = await _post(f"/repos/{owner}/{repo}/releases", {
                    "tag_name":   params["tag"],
                    "name":       params.get("name", params["tag"]),
                    "body":       params.get("body", ""),
                    "draft":      params.get("draft", False),
                    "prerelease": params.get("prerelease", False),
                })
                return SkillOutput(data={"result": {"id": data["id"], "url": data["html_url"]}})

            # ── Search ───────────────────────────────────────────────────
            if action == "search_code":
                q = params["query"]
                if owner and repo and "repo:" not in q:
                    q = f"{q} repo:{owner}/{repo}"
                data = await _get("/search/code",
                                  {"q": q, "per_page": params.get("per_page", 10)})
                return SkillOutput(data={"result": [
                    {"name": i["name"], "path": i["path"], "repo": i["repository"]["full_name"],
                     "url": i["html_url"]}
                    for i in data.get("items", [])
                ], "pagination": {"total": data.get("total_count", 0)}})

            # ── Users ────────────────────────────────────────────────────
            if action == "get_user":
                data = await _get(f"/users/{params.get('username', owner)}")
                return SkillOutput(data={"result": {
                    "login": data["login"], "name": data.get("name"),
                    "bio": data.get("bio"), "public_repos": data["public_repos"],
                    "followers": data["followers"], "url": data["html_url"],
                }})

            if action == "list_collaborators":
                data = await _get(f"/repos/{owner}/{repo}/collaborators")
                return SkillOutput(data={"result": [{"login": u["login"], "role": u.get("role_name")} for u in data]})

            return SkillOutput.fail(f"Unknown action: '{action}'. See input_schema for available actions.")

        except Exception as e:
            return SkillOutput.fail(str(e))
