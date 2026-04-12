"""GitHub skill — interact with GitHub repos via API."""
import httpx
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput
from agentforge.skills.registry import register

@register
class GitHubSkill(BaseSkill):
    name = 'github'
    description = 'Interact with GitHub: read files, list issues, search repos, create issues'
    category = 'tool_use'

    async def execute(self, input: SkillInput) -> SkillOutput:
        action = input.data.get('action', 'get_repo')
        token = input.data.get('token', '')
        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'} if token else {}

        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            if action == 'get_repo':
                owner = input.data.get('owner', '')
                repo = input.data.get('repo', '')
                r = await client.get(f'https://api.github.com/repos/{owner}/{repo}')
                r.raise_for_status()
                d = r.json()
                return SkillOutput.ok({'name': d['full_name'], 'description': d['description'],
                                        'stars': d['stargazers_count'], 'forks': d['forks_count'],
                                        'language': d['language'], 'url': d['html_url']})
            elif action == 'list_issues':
                owner, repo = input.data.get('owner'), input.data.get('repo')
                r = await client.get(f'https://api.github.com/repos/{owner}/{repo}/issues',
                                      params={'state': input.data.get('state', 'open'), 'per_page': 10})
                r.raise_for_status()
                return SkillOutput.ok([{'number': i['number'], 'title': i['title'], 'state': i['state']} for i in r.json()])
            elif action == 'search_repos':
                q = input.data.get('query', '')
                r = await client.get('https://api.github.com/search/repositories', params={'q': q, 'per_page': 5})
                r.raise_for_status()
                return SkillOutput.ok([{'name': i['full_name'], 'description': i['description'], 'stars': i['stargazers_count']} for i in r.json().get('items', [])])
            else:
                return SkillOutput.fail(f'Unknown action: {action}')
