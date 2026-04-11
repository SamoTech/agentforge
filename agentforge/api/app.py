"""FastAPI application factory."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from agentforge.core.config import settings
from agentforge.db.base import engine, Base
from agentforge.api.routes import agents, tasks, auth, billing, skills, websocket

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(
        title='AgentForge API',
        description='Production-ready AI Agent Platform',
        version='1.0.0',
        lifespan=lifespan,
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
                       allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.include_router(auth.router, prefix='/auth', tags=['auth'])
    app.include_router(agents.router, prefix='/agents', tags=['agents'])
    app.include_router(tasks.router, prefix='/tasks', tags=['tasks'])
    app.include_router(billing.router, prefix='/billing', tags=['billing'])
    app.include_router(skills.router, prefix='/skills', tags=['skills'])
    app.include_router(websocket.router, prefix='/ws', tags=['websocket'])
    return app

app = create_app()
