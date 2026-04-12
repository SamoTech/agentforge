"""
Advanced GitHub Skill v2
Features: full repo/PR/issue/branch/commit management, code search,
          CI status, file CRUD, release management, org support.
"""
from __future__ import annotations

import base64
import os
from typing import Any, Optional

import httpx

from agentforge.skills.base import BaseSkill, SkillCategory, SkillConfig


class GitHubSkill(BaseSkill):
    name = "github"
    description = (
        "Full GitHub integration: repos, PRs, issues, branches, commits, "
        "code search, CI/Actions status, file CRUD, and release management."
    )
    category = SkillCategory.GITHUB
    version = "2.0.0"
    tags = ["github", "git", "devops", "pr", "issues", "ci", "repos", "code-search"]

    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "get_repo", "list_repos", "create_repo",
                    "get_file", "create_file", "update_file", "delete_file",
                    "list_prs", "get_pr", "create_pr", "merge_pr", "review_pr",
                    "list_issues", "create_issue", "close_issue", "comment_issue",
                    "list_branches", "create_branch", "delete_branch",
                    "list_commits", "get_commit",
                    "search_code", "search_repos",
                    "get_actions_runs", "create_release", "list_releases",
                    "get_user", "list_org_repos",
                ],
            },
            "owner": {"type": "string"},
            "repo": {"type": "string"},
            "params": {"type": "object", "description": "Action-specific parameters"},
        },
        "required": ["action"],
    }

    def __init__(self, token: Optional[str] = None):
        super().__init__(SkillConfig(timeout_seconds=30, max_retries=3, cache_ttl_seconds=60))
        self._token = token or os.getenv("GITHUB_TOKEN", "")
        self._base = "https://api.github.com"

    def _headers(self) -> dict:
        h = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def _api(
        self,
        method: str,
        path: str,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Any:
        async with httpx.AsyncClient(headers=self._headers(), timeout=25.0) as client:
            resp = await client.request(
                method, f"{self._base}{path}", json=json, params=params
            )
            if resp.status_code == 404:
                return {"error": "Not found", "status": 404}
            resp.raise_for_status()
            if resp.status_code == 204:
                return {"success": True}
            return resp.json()

    async def _execute(
        self,
        action: str,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        params: Optional[dict] = None,
        **kwargs,
    ) -> Any:
        p = params or {}

        match action:
            case "get_repo":
                return await self._api("GET", f"/repos/{owner}/{repo}")

            case "list_repos":
                username = p.get("username", owner)
                return await self._api("GET", f"/users/{username}/repos",
                    params={"per_page": p.get("per_page", 30), "sort": "updated"})

            case "create_repo":
                return await self._api("POST", "/user/repos", json={
                    "name": p["name"], "description": p.get("description", ""),
                    "private": p.get("private", False), "auto_init": p.get("auto_init", True),
                })

            case "get_file":
                query = {"ref": p["ref"]} if p.get("ref") else {}
                data = await self._api("GET", f"/repos/{owner}/{repo}/contents/{p.get('path', '')}", params=query)
                if isinstance(data, dict) and "content" in data:
                    data["decoded_content"] = base64.b64decode(
                        data["content"].replace("\n", "")
                    ).decode("utf-8", errors="replace")
                return data

            case "create_file":
                return await self._api("PUT", f"/repos/{owner}/{repo}/contents/{p['path']}", json={
                    "message": p.get("message", "Create file via AgentForge"),
                    "content": base64.b64encode(p["content"].encode()).decode(),
                    "branch": p.get("branch", "main"),
                })

            case "update_file":
                return await self._api("PUT", f"/repos/{owner}/{repo}/contents/{p['path']}", json={
                    "message": p.get("message", "Update file via AgentForge"),
                    "content": base64.b64encode(p["content"].encode()).decode(),
                    "sha": p["sha"], "branch": p.get("branch", "main"),
                })

            case "delete_file":
                return await self._api("DELETE", f"/repos/{owner}/{repo}/contents/{p['path']}", json={
                    "message": p.get("message", "Delete file via AgentForge"),
                    "sha": p["sha"], "branch": p.get("branch", "main"),
                })

            case "list_prs":
                return await self._api("GET", f"/repos/{owner}/{repo}/pulls",
                    params={"state": p.get("state", "open"), "per_page": p.get("per_page", 20)})

            case "get_pr":
                return await self._api("GET", f"/repos/{owner}/{repo}/pulls/{p['number']}")

            case "create_pr":
                return await self._api("POST", f"/repos/{owner}/{repo}/pulls", json={
                    "title": p["title"], "body": p.get("body", ""),
                    "head": p["head"], "base": p.get("base", "main"),
                    "draft": p.get("draft", False),
                })

            case "merge_pr":
                return await self._api("PUT", f"/repos/{owner}/{repo}/pulls/{p['number']}/merge", json={
                    "merge_method": p.get("merge_method", "squash"),
                    "commit_title": p.get("commit_title", ""),
                })

            case "review_pr":
                return await self._api("POST", f"/repos/{owner}/{repo}/pulls/{p['number']}/reviews", json={
                    "body": p.get("body", ""),
                    "event": p.get("event", "COMMENT"),
                    "comments": p.get("comments", []),
                })

            case "list_issues":
                return await self._api("GET", f"/repos/{owner}/{repo}/issues",
                    params={"state": p.get("state", "open"), "labels": p.get("labels", ""),
                            "per_page": p.get("per_page", 20)})

            case "create_issue":
                return await self._api("POST", f"/repos/{owner}/{repo}/issues", json={
                    "title": p["title"], "body": p.get("body", ""),
                    "labels": p.get("labels", []), "assignees": p.get("assignees", []),
                })

            case "close_issue":
                return await self._api("PATCH", f"/repos/{owner}/{repo}/issues/{p['number']}",
                    json={"state": "closed"})

            case "comment_issue":
                return await self._api("POST", f"/repos/{owner}/{repo}/issues/{p['number']}/comments",
                    json={"body": p["body"]})

            case "list_branches":
                return await self._api("GET", f"/repos/{owner}/{repo}/branches",
                    params={"per_page": p.get("per_page", 30)})

            case "create_branch":
                ref_data = await self._api("GET",
                    f"/repos/{owner}/{repo}/git/ref/heads/{p.get('from_branch', 'main')}")
                sha = ref_data["object"]["sha"]
                return await self._api("POST", f"/repos/{owner}/{repo}/git/refs", json={
                    "ref": f"refs/heads/{p['branch']}", "sha": sha,
                })

            case "delete_branch":
                return await self._api("DELETE",
                    f"/repos/{owner}/{repo}/git/refs/heads/{p['branch']}")

            case "list_commits":
                return await self._api("GET", f"/repos/{owner}/{repo}/commits",
                    params={"sha": p.get("sha", ""), "per_page": p.get("per_page", 20),
                            "author": p.get("author", "")})

            case "get_commit":
                return await self._api("GET", f"/repos/{owner}/{repo}/commits/{p['sha']}")

            case "search_code":
                return await self._api("GET", "/search/code",
                    params={"q": p["query"], "per_page": p.get("per_page", 10)})

            case "search_repos":
                return await self._api("GET", "/search/repositories",
                    params={"q": p["query"], "sort": p.get("sort", "stars"),
                            "per_page": p.get("per_page", 10)})

            case "get_actions_runs":
                return await self._api("GET", f"/repos/{owner}/{repo}/actions/runs",
                    params={"per_page": p.get("per_page", 10), "status": p.get("status", "")})

            case "create_release":
                return await self._api("POST", f"/repos/{owner}/{repo}/releases", json={
                    "tag_name": p["tag"], "name": p.get("name", p["tag"]),
                    "body": p.get("body", ""), "draft": p.get("draft", False),
                    "prerelease": p.get("prerelease", False),
                })

            case "list_releases":
                return await self._api("GET", f"/repos/{owner}/{repo}/releases",
                    params={"per_page": p.get("per_page", 10)})

            case "get_user":
                return await self._api("GET", f"/users/{p.get('username', owner)}")

            case "list_org_repos":
                return await self._api("GET", f"/orgs/{owner}/repos",
                    params={"per_page": p.get("per_page", 30), "type": p.get("type", "all")})

            case _:
                return {"error": f"Unknown action: {action}"}
