"""
Advanced Web Scraper Skill v2
Features: full HTML parsing, CSS selector extraction, link following,
          structured data (JSON-LD), metadata, images, multi-page crawl,
          content cleaning, anti-bot headers.
"""
from __future__ import annotations

import asyncio
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from agentforge.skills.base import BaseSkill, SkillCategory, SkillConfig


class WebScraperSkill(BaseSkill):
    name = "web_scraper"
    description = (
        "Scrapes web pages with full HTML parsing, CSS selector extraction, "
        "link following, structured data extraction (JSON-LD), metadata, "
        "and optional multi-page crawling."
    )
    category = SkillCategory.SEARCH
    version = "2.0.0"
    tags = ["web", "scraping", "html", "data-extraction", "research", "crawl"]

    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to scrape"},
            "selectors": {
                "type": "object",
                "description": "CSS selectors map e.g. {'title': 'h1', 'body': 'article'}",
            },
            "extract_links": {"type": "boolean", "default": False},
            "extract_images": {"type": "boolean", "default": False},
            "follow_links": {"type": "boolean", "default": False},
            "max_depth": {"type": "integer", "default": 1},
            "clean_text": {"type": "boolean", "default": True},
            "extract_metadata": {"type": "boolean", "default": True},
        },
        "required": ["url"],
    }

    def __init__(self):
        super().__init__(SkillConfig(timeout_seconds=30, max_retries=3, cache_ttl_seconds=600))
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    async def _fetch(self, url: str) -> tuple[str, int]:
        async with httpx.AsyncClient(
            headers=self._headers,
            follow_redirects=True,
            timeout=25.0,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text, resp.status_code

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> dict:
        meta = {
            "url": url, "title": "", "description": "",
            "keywords": [], "og": {}, "canonical": "", "lang": "",
        }
        if soup.title:
            meta["title"] = soup.title.get_text(strip=True)
        for tag in soup.find_all("meta"):
            name = tag.get("name", "").lower()
            prop = tag.get("property", "").lower()
            content = tag.get("content", "")
            if name == "description":
                meta["description"] = content
            elif name == "keywords":
                meta["keywords"] = [k.strip() for k in content.split(",")]
            elif prop.startswith("og:"):
                meta["og"][prop[3:]] = content
        canonical = soup.find("link", rel="canonical")
        if canonical:
            meta["canonical"] = canonical.get("href", "")
        html_tag = soup.find("html")
        if html_tag:
            meta["lang"] = html_tag.get("lang", "")
        return meta

    def _extract_structured_data(self, soup: BeautifulSoup) -> list[dict]:
        import json
        results = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                results.append(data)
            except Exception:
                pass
        return results

    def _apply_selectors(self, soup: BeautifulSoup, selectors: dict) -> dict:
        extracted = {}
        for key, selector in selectors.items():
            elements = soup.select(selector)
            if not elements:
                extracted[key] = None
            elif len(elements) == 1:
                extracted[key] = elements[0].get_text(strip=True)
            else:
                extracted[key] = [e.get_text(strip=True) for e in elements]
        return extracted

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            full_url = urljoin(base_url, a["href"])
            parsed = urlparse(full_url)
            if parsed.scheme in ("http", "https") and full_url not in seen:
                seen.add(full_url)
                links.append({
                    "url": full_url,
                    "text": a.get_text(strip=True),
                    "domain": parsed.netloc,
                })
        return links

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        images = []
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src", "")
            if src:
                images.append({
                    "url": urljoin(base_url, src),
                    "alt": img.get("alt", ""),
                    "width": img.get("width"),
                    "height": img.get("height"),
                })
        return images

    async def _execute(
        self,
        url: str,
        selectors: Optional[dict] = None,
        extract_links: bool = False,
        extract_images: bool = False,
        follow_links: bool = False,
        max_depth: int = 1,
        clean_text: bool = True,
        extract_metadata: bool = True,
        **kwargs,
    ) -> Any:
        html, status_code = await self._fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "noscript", "nav", "footer", "aside"]):
            tag.decompose()

        result: dict = {"url": url, "status_code": status_code}

        main = soup.find("main") or soup.find("article") or soup.find("body")
        raw_text = main.get_text(separator="\n") if main else soup.get_text(separator="\n")
        result["content"] = self._clean_text(raw_text) if clean_text else raw_text
        result["word_count"] = len(result["content"].split())
        result["char_count"] = len(result["content"])

        if extract_metadata:
            result["metadata"] = self._extract_metadata(soup, url)
            result["structured_data"] = self._extract_structured_data(soup)

        if selectors:
            result["extracted"] = self._apply_selectors(soup, selectors)

        if extract_links:
            all_links = self._extract_links(soup, url)
            result["links"] = all_links
            base_domain = urlparse(url).netloc
            result["internal_links"] = [link for link in all_links if urlparse(link["url"]).netloc == base_domain]
            result["external_links"] = [link for link in all_links if urlparse(link["url"]).netloc != base_domain]

        if extract_images:
            result["images"] = self._extract_images(soup, url)

        if follow_links and max_depth > 1:
            child_links = self._extract_links(soup, url)
            same_domain = [
                link["url"] for link in child_links
                if urlparse(link["url"]).netloc == urlparse(url).netloc
            ][:5]
            child_results = await asyncio.gather(
                *[self._execute(child_url, max_depth=max_depth - 1) for child_url in same_domain],
                return_exceptions=True,
            )
            result["crawled_pages"] = [r for r in child_results if not isinstance(r, Exception)]

        return result
