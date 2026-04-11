"""Web search skill — search the web via SerpAPI or DuckDuckGo."""
import httpx
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput
from agentforge.skills.registry import register

@register
class WebSearchSkill(BaseSkill):
    name = 'web_search'
    description = 'Search the web and return top results with titles, URLs, and snippets'
    category = 'search'

    async def execute(self, input: SkillInput) -> SkillOutput:
        query = input.data.get('query', '')
        num_results = input.data.get('num_results', 5)
        if not query: return SkillOutput.fail('query is required')

        # Try DuckDuckGo Instant Answer API (no key required)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    'https://api.duckduckgo.com/',
                    params={'q': query, 'format': 'json', 'no_redirect': 1, 'no_html': 1},
                )
                data = r.json()
                results = []
                if data.get('AbstractText'):
                    results.append({'title': data.get('Heading', 'Abstract'), 'snippet': data['AbstractText'], 'url': data.get('AbstractURL', '')})
                for item in data.get('RelatedTopics', [])[:num_results]:
                    if isinstance(item, dict) and item.get('Text'):
                        results.append({'title': item.get('Text', '')[:80], 'snippet': item.get('Text', ''), 'url': item.get('FirstURL', '')})
                return SkillOutput.ok({'query': query, 'results': results[:num_results], 'source': 'duckduckgo'})
        except Exception as e:
            return SkillOutput.fail(f'Search failed: {e}')
