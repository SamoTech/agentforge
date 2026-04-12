"""
Advanced Web Search Skill v2
Features: multi-provider (DuckDuckGo free, Tavily, Brave, SerpAPI),
          auto provider selection, deduplication, result ranking,
          news/web/academic search types, time-range filtering.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from agentforge.skills.base import BaseSkill, SkillCategory, SkillConfig


class WebSearchSkill(BaseSkill):
    name = "web_search"
    description = (
        "Multi-provider web search with automatic provider selection. "
        "Supports DuckDuckGo (free), Tavily, Brave Search. "
        "Returns ranked, deduplicated results with snippets and metadata."
    )
    category = SkillCategory.SEARCH
    version = "2.0.0"
    tags = ["search", "web", "research", "duckduckgo", "tavily", "brave", "news"]

    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "provider": {
                "type": "string",
                "enum": ["auto", "duckduckgo", "tavily", "brave"],
                "default": "auto",
            },
            "num_results": {"type": "integer", "default": 10},
            "search_type": {
                "type": "string",
                "enum": ["web", "news"],
                "default": "web",
            },
            "region": {"type": "string", "default": "wt-wt"},
            "time_range": {
                "type": "string",
                "enum": ["day", "week", "month", "year", ""],
                "default": "",
            },
        },
        "required": ["query"],
    }

    def __init__(self):
        super().__init__(SkillConfig(timeout_seconds=20, max_retries=3, cache_ttl_seconds=300))
        self._tavily_key = os.getenv("TAVILY_API_KEY", "")
        self._brave_key = os.getenv("BRAVE_SEARCH_KEY", "")

    def _select_provider(self) -> str:
        if self._tavily_key:
            return "tavily"
        if self._brave_key:
            return "brave"
        return "duckduckgo"

    async def _search_duckduckgo(self, query: str, num: int, region: str, time_range: str) -> list[dict]:
        params: dict = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1", "kl": region}
        if time_range:
            params["df"] = time_range[:1]
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get("https://api.duckduckgo.com/", params=params)
            data = resp.json()

        results = []
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", ""),
                "url": data.get("AbstractURL", ""),
                "snippet": data["AbstractText"],
                "source": data.get("AbstractSource", ""),
                "type": "instant_answer",
            })
        for topic in data.get("RelatedTopics", [])[:num]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "url": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", ""),
                    "source": "duckduckgo",
                    "type": "related",
                })

        if len(results) < 3:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; AgentForge/2.0)"}
                async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                    resp = await client.get("https://html.duckduckgo.com/html/",
                        params={"q": query, "kl": region})
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                for r in soup.select(".result__body")[:num]:
                    title_el = r.select_one(".result__title")
                    url_el = r.select_one(".result__url")
                    snippet_el = r.select_one(".result__snippet")
                    if title_el and snippet_el:
                        results.append({
                            "title": title_el.get_text(strip=True),
                            "url": url_el.get_text(strip=True) if url_el else "",
                            "snippet": snippet_el.get_text(strip=True),
                            "source": "duckduckgo", "type": "web",
                        })
            except Exception:
                pass
        return results[:num]

    async def _search_tavily(self, query: str, num: int, search_type: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://api.tavily.com/search", json={
                "api_key": self._tavily_key, "query": query,
                "max_results": num, "search_depth": "advanced",
                "include_answer": True, "include_raw_content": False,
                "topic": "news" if search_type == "news" else "general",
            })
            data = resp.json()
        results = []
        if data.get("answer"):
            results.append({"title": "AI Answer", "url": "", "snippet": data["answer"],
                "type": "ai_answer", "source": "tavily"})
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""), "url": r.get("url", ""),
                "snippet": r.get("content", ""), "score": r.get("score", 0),
                "published_date": r.get("published_date", ""),
                "source": "tavily", "type": "web",
            })
        return results

    async def _search_brave(self, query: str, num: int, time_range: str) -> list[dict]:
        params: dict = {"q": query, "count": num}
        if time_range:
            params["freshness"] = {"day": "pd", "week": "pw", "month": "pm"}.get(time_range, "")
        async with httpx.AsyncClient(
            headers={"Accept": "application/json", "X-Subscription-Token": self._brave_key},
            timeout=15.0,
        ) as client:
            resp = await client.get("https://api.search.brave.com/res/v1/web/search", params=params)
            data = resp.json()
        return [
            {"title": r.get("title", ""), "url": r.get("url", ""),
             "snippet": r.get("description", ""), "source": "brave", "type": "web"}
            for r in data.get("web", {}).get("results", [])
        ]

    def _deduplicate(self, results: list[dict]) -> list[dict]:
        seen_urls, seen_snippets, deduped = set(), set(), []
        for r in results:
            url = r.get("url", "")
            snippet_key = r.get("snippet", "")[:50]
            if url and url not in seen_urls and snippet_key not in seen_snippets:
                seen_urls.add(url)
                seen_snippets.add(snippet_key)
                deduped.append(r)
        return deduped

    async def _execute(
        self,
        query: str,
        provider: str = "auto",
        num_results: int = 10,
        search_type: str = "web",
        region: str = "wt-wt",
        time_range: str = "",
        **kwargs,
    ) -> Any:
        if not query:
            return {"error": "query is required"}
        if provider == "auto":
            provider = self._select_provider()

        try:
            match provider:
                case "tavily":
                    results = await self._search_tavily(query, num_results, search_type)
                case "brave":
                    results = await self._search_brave(query, num_results, time_range)
                case _:
                    results = await self._search_duckduckgo(query, num_results, region, time_range)
        except Exception:
            results = await self._search_duckduckgo(query, num_results, region, time_range)

        deduped = self._deduplicate(results)
        return {
            "query": query, "provider": provider,
            "total_results": len(deduped),
            "results": deduped[:num_results],
            "search_type": search_type,
        }
