"""Web scraper skill — fetch and parse web page content."""
import httpx
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput
from agentforge.skills.registry import register

@register
class WebScraperSkill(BaseSkill):
    name = 'web_scraper'
    description = 'Fetch and extract clean text content from any URL'
    category = 'perception'

    async def execute(self, input: SkillInput) -> SkillOutput:
        url = input.data.get('url')
        if not url: return SkillOutput.fail('url is required')
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(url, headers={'User-Agent': 'AgentForge/1.0'})
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            return SkillOutput.fail(f'HTTP {e.response.status_code}: {url}')
        except httpx.RequestError as e:
            return SkillOutput.fail(f'Request failed: {e}')
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            text = soup.get_text(separator='\n', strip=True)
            return SkillOutput.ok({'text': text[:5000], 'url': url, 'title': soup.title.string if soup.title else ''})
        except ImportError:
            return SkillOutput.ok({'text': response.text[:5000], 'url': url, 'title': ''})
