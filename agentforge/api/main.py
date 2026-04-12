"""FastAPI application factory."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from agentforge.core.config import settings
from agentforge.core.logger import logger
from agentforge.skills.registry import SkillRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("agentforge_start", env=settings.app_env)
    registry = SkillRegistry()
    count = registry.auto_discover("agentforge.skills.catalog")
    app.state.skill_registry = registry
    logger.info("skills_loaded", count=count)
    yield
    logger.info("agentforge_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgentForge API",
        description="Mega AI Agent Platform — 10,000+ skills, multi-agent orchestration",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────
    from agentforge.api.routes import auth, agents, tasks, skills, billing, ws, admin
    app.include_router(auth.router,    prefix="/auth",    tags=["Auth"])
    app.include_router(agents.router,  prefix="/agents",  tags=["Agents"])
    app.include_router(tasks.router,   prefix="/tasks",   tags=["Tasks"])
    app.include_router(skills.router,  prefix="/skills",  tags=["Skills"])
    app.include_router(billing.router, prefix="/billing", tags=["Billing"])
    app.include_router(ws.router,      prefix="/ws",      tags=["WebSocket"])
    app.include_router(admin.router,   prefix="/admin",   tags=["Admin"])

    @app.get("/health", tags=["System"])
    async def health():
        reg = getattr(app.state, "skill_registry", None)
        return {"status": "ok", "version": "0.1.0", "env": settings.app_env,
                "skills": len(reg) if reg else 0}

    return app


app = create_app()
