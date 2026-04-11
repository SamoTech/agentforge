#!/usr/bin/env bash
set -euo pipefail

echo "🤖 AgentForge Setup"
echo "==================="

command -v python3.11 &>/dev/null || { echo "❌ Python 3.11+ required"; exit 1; }
command -v docker &>/dev/null || { echo "❌ Docker required"; exit 1; }

[ ! -f .env ] && cp .env.example .env && echo "✅ .env created — fill in your API keys"

pip install -e '.[dev]' --quiet
echo "✅ Python deps installed"

docker compose -f docker/docker-compose.yml up -d postgres redis chroma
echo "✅ Services started"

echo "⏳ Waiting for Postgres..."
until docker compose -f docker/docker-compose.yml exec -T postgres pg_isready -U agentforge &>/dev/null; do sleep 1; done
echo "✅ Postgres ready"

alembic upgrade head
echo "✅ Database migrated"

if command -v npm &>/dev/null; then
  cd frontend && npm install --silent && cd ..
  echo "✅ Frontend deps installed"
fi

echo ""
echo "🎉 AgentForge is ready!"
echo "  API:      uvicorn agentforge.api.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo "  CLI:      agentforge --help"
echo "  Docs:     http://localhost:8000/docs"
