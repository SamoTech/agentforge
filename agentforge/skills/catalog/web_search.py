"""Skill: web_search — search the web using DuckDuckGo or SerpAPI."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class WebSearchSkill(BaseSkill):
    name = "web_search"
    description = "Search the web and return top results with titles, URLs, and snippets."
    category = "web"
    tags = ["search", "internet", "research", "duckduckgo"]
    level = "basic"
    requires_network = True
    input_schema = {
        "query":    {"type": "string",  "required": True,  "description": "Search query"},
        "num":      {"type": "integer", "required": False, "description": "Results to return (default 5)"},
        "provider": {"type": "string",  "required": False, "description": "duckduckgo | serpapi"},
    }
    output_schema = {
        "results": {"type": "array", "description": "List of {title, url, snippet}"}
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        query = inp.data.get("query", "")
        num   = int(inp.data.get("num", 5))
        if not query:
            return SkillOutput.fail("query is required")
        try:
            import httpx
            # DuckDuckGo Instant Answer API (no key required)
            url = "https://api.duckduckgo.com/"
            params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url, params=params)
            data = r.json()
            results = []
            for topic in (data.get("RelatedTopics") or [])[:num]:
                if "FirstURL" in topic:
                    results.append({
                        "title":   topic.get("Text", "")[:120],
                        "url":     topic["FirstURL"],
                        "snippet": topic.get("Text", ""),
                    })
            # Also include the abstract if present
            if data.get("AbstractURL"):
                results.insert(0, {
                    "title":   data.get("Heading", query),
                    "url":     data["AbstractURL"],
                    "snippet": data.get("AbstractText", ""),
                })
            return SkillOutput(data={"results": results[:num]})
        except Exception as e:
            return SkillOutput.fail(str(e))
