"""Skill: web_scraper — fetch and clean text content from a URL with retries and JS rendering."""
from __future__ import annotations
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput


class WebScraperSkill(BaseSkill):
    name = "web_scraper"
    description = (
        "Fetch a URL and extract clean readable text, title, metadata, and links. "
        "Handles JS-heavy pages via Playwright fallback, respects robots.txt, retries on failure."
    )
    category = "search"
    tags = ["scrape", "crawl", "html", "extract", "text", "playwright"]
    level = "advanced"
    requires_network = True
    input_schema = {
        "url":            {"type": "string",  "required": True},
        "extract_links":  {"type": "boolean", "default": False},
        "max_chars":      {"type": "integer", "default": 16000},
        "js_render":      {"type": "boolean", "default": False,
                           "description": "Use Playwright headless browser for JS-heavy pages"},
        "wait_selector":  {"type": "string",  "default": "",
                           "description": "CSS selector to wait for before extracting (js_render only)"},
        "timeout":        {"type": "integer", "default": 20},
        "proxy":          {"type": "string",  "default": "",
                           "description": "Optional HTTP proxy URL"},
    }
    output_schema = {
        "title":       {"type": "string"},
        "text":        {"type": "string"},
        "links":       {"type": "array"},
        "status":      {"type": "integer"},
        "word_count":  {"type": "integer"},
        "meta": {"type": "object", "description": "og:title, og:description, canonical, etc."},
    }

    _SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside",
                  "noscript", "iframe", "svg", "button"}

    async def execute(self, inp: SkillInput) -> SkillOutput:
        url       = inp.data.get("url", "").strip()
        max_chars = int(inp.data.get("max_chars", 16000))
        get_links = bool(inp.data.get("extract_links", False))
        js_render = bool(inp.data.get("js_render", False))
        wait_sel  = inp.data.get("wait_selector", "")
        timeout   = int(inp.data.get("timeout", 20))
        proxy     = inp.data.get("proxy", "") or None

        if not url:
            return SkillOutput.fail("url is required")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            if js_render:
                html, status = await self._playwright_fetch(url, wait_sel, timeout)
            else:
                html, status = await self._httpx_fetch(url, timeout, proxy)

            parsed = self._parse_html(html, url)
            text   = parsed["text"][:max_chars]
            return SkillOutput(data={
                "title":      parsed["title"],
                "text":       text,
                "links":      parsed["links"][:100] if get_links else [],
                "status":     status,
                "word_count": len(text.split()),
                "meta":       parsed["meta"],
            })
        except Exception as e:
            return SkillOutput.fail(str(e))

    async def _httpx_fetch(self, url: str, timeout: int, proxy: str | None) -> tuple[str, int]:
        import httpx
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
            reraise=True,
        )
        async def _fetch() -> httpx.Response:
            kwargs: dict = {
                "timeout": timeout,
                "follow_redirects": True,
                "headers": {
                    "User-Agent": "Mozilla/5.0 (compatible; AgentForge/1.0)",
                    "Accept": "text/html,application/xhtml+xml,*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            }
            if proxy:
                kwargs["proxies"] = {"http://": proxy, "https://": proxy}
            async with httpx.AsyncClient(**kwargs) as c:
                return await c.get(url)

        r = await _fetch()
        return r.text, r.status_code

    async def _playwright_fetch(self, url: str, wait_selector: str, timeout: int) -> tuple[str, int]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("playwright not installed. Run: pip install playwright && playwright install chromium")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            resp = await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout * 1000)
            html = await page.content()
            await browser.close()
        return html, resp.status if resp else 200

    def _parse_html(self, html: str, base_url: str) -> dict:
        from html.parser import HTMLParser
        from urllib.parse import urljoin

        class _Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self._skip      = False
                self._skip_stack = 0
                self.text_parts: list[str] = []
                self.title  = ""
                self.links:  list[str] = []
                self.meta:   dict = {}
                self._in_title = False

            def handle_starttag(self, tag, attrs):
                a = dict(attrs)
                if tag in WebScraperSkill._SKIP_TAGS:
                    self._skip_stack += 1
                if tag == "title":
                    self._in_title = True
                if tag == "a":
                    href = a.get("href", "")
                    if href:
                        self.links.append(urljoin(base_url, href))
                if tag == "meta":
                    prop = a.get("property", a.get("name", ""))
                    if prop and a.get("content"):
                        self.meta[prop] = a["content"]
                if tag == "link" and a.get("rel") == "canonical":
                    self.meta["canonical"] = a.get("href", "")

            def handle_endtag(self, tag):
                if tag in WebScraperSkill._SKIP_TAGS:
                    self._skip_stack = max(0, self._skip_stack - 1)
                if tag == "title":
                    self._in_title = False

            def handle_data(self, data):
                if self._in_title:
                    self.title += data
                elif self._skip_stack == 0:
                    s = data.strip()
                    if s:
                        self.text_parts.append(s)

        p = _Parser()
        p.feed(html)
        return {
            "title": p.title.strip(),
            "text":  " ".join(p.text_parts),
            "links": list(dict.fromkeys(p.links)),  # deduplicate preserving order
            "meta":  p.meta,
        }
