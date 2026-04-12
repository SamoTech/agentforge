"""Skill: web_search — search the web using SerpAPI, Brave, or DuckDuckGo."""
from __future__ import annotations
import os
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class WebSearchSkill(BaseSkill):
    name = "web_search"
    description = (
        "Search the web and return top results with titles, URLs, and snippets. "
        "Supports SerpAPI (richest results), Brave Search API, and DuckDuckGo (no key)."
    )
    category = "search"
    tags = ["search", "internet", "research", "serpapi", "brave", "duckduckgo"]
    level = "advanced"
    requires_network = True
    input_schema = {
        "query":    {"type": "string",  "required": True,  "description": "Search query"},
        "num":      {"type": "integer", "default": 8,     "description": "Max results to return"},
        "provider": {"type": "string",  "default": "auto",
                     "description": "auto | serpapi | brave | duckduckgo. auto picks best available."},
        "region":   {"type": "string",  "default": "us",  "description": "Region/locale code"},
        "safe":     {"type": "boolean", "default": True,  "description": "Enable safe-search"},
    }
    output_schema = {
        "results":  {"type": "array",   "description": "[{title, url, snippet, source}]"},
        "provider_used": {"type": "string"},
        "total_results": {"type": "integer"},
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        query    = inp.data.get("query", "")
        num      = int(inp.data.get("num", 8))
        provider = inp.data.get("provider", "auto")
        if not query:
            return SkillOutput.fail("query is required")

        # Auto-select best available provider based on env keys
        if provider == "auto":
            if os.getenv("SERPAPI_KEY"):
                provider = "serpapi"
            elif os.getenv("BRAVE_SEARCH_KEY"):
                provider = "brave"
            else:
                provider = "duckduckgo"

        try:
            if provider == "serpapi":
                results = await self._serpapi(query, num, inp.data)
            elif provider == "brave":
                results = await self._brave(query, num, inp.data)
            else:
                results = await self._duckduckgo(query, num)

            return SkillOutput(data={
                "results":       results[:num],
                "provider_used": provider,
                "total_results": len(results),
            })
        except Exception as e:
            return SkillOutput.fail(str(e))

    # ── Providers ─────────────────────────────────────────────────────────

    async def _serpapi(self, query: str, num: int, inp_data: dict) -> list[dict]:
        import httpx
        params = {
            "q":      query,
            "num":    num,
            "hl":     inp_data.get("region", "us"),
            "safe":   "active" if inp_data.get("safe", True) else "off",
            "api_key": os.getenv("SERPAPI_KEY"),
            "engine": "google",
        }
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get("https://serpapi.com/search", params=params)
            r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source":  item.get("source", ""),
            })
        return results

    async def _brave(self, query: str, num: int, inp_data: dict) -> list[dict]:
        import httpx
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": os.getenv("BRAVE_SEARCH_KEY", ""),
        }
        params = {
            "q":     query,
            "count": num,
            "country": inp_data.get("region", "US").upper(),
            "safesearch": "strict" if inp_data.get("safe", True) else "off",
        }
        async with httpx.AsyncClient(timeout=15, headers=headers) as c:
            r = await c.get("https://api.search.brave.com/res/v1/web/search", params=params)
            r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("url", ""),
                "snippet": item.get("description", ""),
                "source":  item.get("meta_url", {}).get("hostname", ""),
            })
        return results

    async def _duckduckgo(self, query: str, num: int) -> list[dict]:
        """Use DDG HTML scrape (more reliable than Instant Answer API)."""
        import httpx, re
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AgentForge/1.0)",
            "Accept-Language": "en-US,en;q=0.9",
        }
        results: list[dict] = []
        try:
            # Try DDG HTML endpoint
            async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as c:
                r = await c.post("https://html.duckduckgo.com/html/",
                                 data={"q": query, "b": "", "kl": "us-en"})
            # Extract results via simple regex (no BS4 dependency)
            titles   = re.findall(r'class="result__a"[^>]*>([^<]+)<', r.text)
            urls     = re.findall(r'class="result__url"[^>]*>\s*([^\s<]+)', r.text)
            snippets = re.findall(r'class="result__snippet"[^>]*>([^<]+)<', r.text)
            for i in range(min(len(titles), len(urls), num)):
                results.append({
                    "title":   titles[i].strip(),
                    "url":     "https://" + urls[i].strip() if not urls[i].startswith("http") else urls[i].strip(),
                    "snippet": snippets[i].strip() if i < len(snippets) else "",
                    "source":  "",
                })
        except Exception:
            pass

        # Fallback: DDG Instant Answer API
        if not results:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get("https://api.duckduckgo.com/",
                                params={"q": query, "format": "json", "no_html": 1})
            data = r.json()
            if data.get("AbstractURL"):
                results.append({
                    "title":   data.get("Heading", query),
                    "url":     data["AbstractURL"],
                    "snippet": data.get("AbstractText", ""),
                    "source":  "",
                })
            for topic in (data.get("RelatedTopics") or [])[:num]:
                if "FirstURL" in topic:
                    results.append({
                        "title":   topic.get("Text", "")[:120],
                        "url":     topic["FirstURL"],
                        "snippet": topic.get("Text", ""),
                        "source":  "",
                    })
        return results
