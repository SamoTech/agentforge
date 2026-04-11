# 🤖 AgentForge

> **Mega AI Agent Platform** — 10,000+ modular skills, multi-agent orchestration, persistent memory, and SaaS-ready infrastructure.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js)](https://nextjs.org)
[![Views](https://komarev.com/ghpvc/?username=SamoTech&repo=agentforge&label=Views&color=0e75b6&style=for-the-badge)](https://github.com/SamoTech/agentforge)

---

## ✨ What Is AgentForge?

AgentForge is a production-ready platform for building, deploying, and orchestrating AI agents at scale. It provides:

- **10,000+ Modular Skills** — plugin-style, dynamically loaded, searchable registry
- **Multi-Agent Orchestration** — Planner, Executor, Specialist, and Memory agents working together
- **Multi-Framework Support** — LangChain, AutoGen, CrewAI, LlamaIndex, OpenAI SDK adapters via unified interface
- **Persistent Memory** — Short-term (Redis), Long-term (ChromaDB/FAISS), and Team-shared memory
- **SaaS Infrastructure** — JWT auth, Stripe billing, usage tracking, admin dashboard
- **CLI Tool** — `agentforge` command for managing everything from the terminal
- **Auto-Skill Generator** — LLM generates new skill modules on demand from natural language

---

## 🗂️ Project Structure

```
agentforge/
├── agentforge/                  # Python backend package
│   ├── api/                     # FastAPI app + all routes
│   ├── agents/                  # Agent roles: planner, executor, specialist, memory
│   ├── skills/                  # Skill system: base class, registry, 10+ catalog skills
│   ├── orchestrator/            # Central orchestrator — routes tasks to agents/skills
│   ├── core/memory/             # Short-term, long-term, team memory
│   ├── frameworks/adapters/     # LangChain, AutoGen, CrewAI adapters
│   ├── auth/                    # JWT + OAuth2 password flow
│   ├── billing/                 # Stripe checkout, portal, webhooks
│   ├── db/                      # SQLAlchemy async models + Alembic migrations
│   ├── cli/                     # Typer CLI tool
│   └── tests/                   # Pytest test suite
├── frontend/                    # Next.js 14 dashboard
├── docker/                      # Docker Compose full stack
├── scripts/                     # Setup & deployment scripts
└── .github/workflows/           # CI/CD pipeline
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js 20+

### 1. Clone
```bash
git clone https://github.com/SamoTech/agentforge.git
cd agentforge
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY at minimum
```

### 3. Start services
```bash
bash scripts/setup.sh
# Starts Postgres, Redis, ChromaDB via Docker
# Installs Python + frontend deps
# Runs DB migrations
```

### 4. Run
```bash
# API (port 8000)
uvicorn agentforge.api.main:app --reload

# Frontend (port 3000)
cd frontend && npm run dev

# CLI
agentforge --help
```

---

## 🧠 Skill System

Every skill is a Python class. Add a new one in seconds:

```python
from agentforge.skills.base import BaseSkill, SkillInput, SkillOutput

class MySkill(BaseSkill):
    name = "my_skill"
    description = "Does something useful"
    category = "custom"
    tags = ["example"]
    input_schema = {"query": {"type": "string", "required": True}}
    output_schema = {"result": {"type": "string"}}

    async def execute(self, inp: SkillInput) -> SkillOutput:
        return SkillOutput(result=f"Processed: {inp.data['query']}")
```

Register via CLI:
```bash
agentforge skills register path/to/my_skill.py
```

Or auto-generate from a description:
```bash
agentforge skills generate "scrape a webpage and extract all links"
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register new user |
| `POST` | `/auth/login` | Get JWT access token |
| `GET` | `/skills/` | List all skills |
| `POST` | `/skills/search` | Search skills by query |
| `POST` | `/skills/generate` | Auto-generate skill from description |
| `GET` | `/agents/` | List user's agents |
| `POST` | `/agents/` | Create agent |
| `POST` | `/tasks/` | Submit task for execution |
| `GET` | `/tasks/{id}` | Poll task result |
| `GET` | `/admin/stats` | Platform-wide stats (admin) |
| `POST` | `/billing/checkout` | Create Stripe checkout session |
| `POST` | `/billing/portal` | Access billing portal |

Full interactive docs: `http://localhost:8000/docs`

---

## 🤖 Agent Roles

| Role | Responsibility |
|------|----------------|
| **Planner** | Breaks complex tasks into sub-tasks, creates execution plans |
| **Executor** | Runs tasks step-by-step, calls skills, reports results |
| **Specialist** | Domain expert (code, research, data analysis, etc.) |
| **Memory** | Manages context retrieval and memory injection |

---

## 📊 Supported Frameworks

| Framework | Adapter | Status |
|-----------|---------|--------|
| OpenAI SDK | Native | ✅ Stable |
| LangChain | `frameworks/adapters/langchain_adapter.py` | ✅ Stable |
| AutoGen | `frameworks/adapters/autogen_adapter.py` | ✅ Stable |
| CrewAI | `frameworks/adapters/crewai_adapter.py` | ✅ Stable |
| LlamaIndex | `frameworks/adapters/llamaindex_adapter.py` | 🚧 Beta |

---

## 💰 Pricing Tiers

| Plan | Price | Agents | Skills/mo | API Calls/mo |
|------|-------|--------|-----------|---------------|
| **Free** | $0 | 2 | 100 | 1,000 |
| **Pro** | $29/mo | 10 | 1,000 | 50,000 |
| **Teams** | $99/mo | 50 | 10,000 | 500,000 |
| **Enterprise** | Custom | ∞ | ∞ | ∞ |

---

## 📄 License

MIT © 2026 [Ossama Hashim](https://github.com/SamoTech)
