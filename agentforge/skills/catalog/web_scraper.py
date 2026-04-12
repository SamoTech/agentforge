"""Skill: web_scraper — fetch and clean text content from a URL."""
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class WebScraperSkill(BaseSkill):
    name = "web_scraper"
    description = "Fetch a URL and extract clean readable text, title, and links."
    category = "web"
    tags = ["scrape", "crawl", "html", "extract", "text"]
    level = "basic"
    requires_network = True
    input_schema = {
        "url":          {"type": "string",  "required": True},
        "extract_links":{"type": "boolean", "required": False, "description": "Return list of links"},
        "max_chars":    {"type": "integer", "required": False, "description": "Truncate text at N chars"},
    }
    output_schema = {
        "title":   {"type": "string"},
        "text":    {"type": "string"},
        "links":   {"type": "array"},
        "status":  {"type": "integer"},
    }

    async def execute(self, inp: SkillInput) -> SkillOutput:
        url       = inp.data.get("url", "")
        max_chars = int(inp.data.get("max_chars", 8000))
        get_links = inp.data.get("extract_links", False)
        if not url:
            return SkillOutput.fail("url is required")
        try:
            import httpx
            from html.parser import HTMLParser

            class _TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._skip = False
                    self.text_parts: list[str] = []
                    self.title = ""
                    self.links: list[str] = []
                    self._in_title = False

                def handle_starttag(self, tag, attrs):
                    if tag in ("script", "style", "nav", "footer"): self._skip = True
                    if tag == "title": self._in_title = True
                    if tag == "a":
                        href = dict(attrs).get("href", "")
                        if href.startswith("http"): self.links.append(href)

                def handle_endtag(self, tag):
                    if tag in ("script", "style", "nav", "footer"): self._skip = False
                    if tag == "title": self._in_title = False

                def handle_data(self, data):
                    if self._in_title: self.title += data
                    elif not self._skip:
                        stripped = data.strip()
                        if stripped: self.text_parts.append(stripped)

            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                r = await client.get(url, headers={"User-Agent": "AgentForge/1.0"})
            parser = _TextExtractor()
            parser.feed(r.text)
            text = " ".join(parser.text_parts)[:max_chars]
            return SkillOutput(data={
                "title":  parser.title.strip(),
                "text":   text,
                "links":  parser.links[:50] if get_links else [],
                "status": r.status_code,
            })
        except Exception as e:
            return SkillOutput.fail(str(e))
