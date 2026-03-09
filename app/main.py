from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.payments import provider_router, router
from app.core.config import get_settings
from app.db.session import engine
from app.redis import redis_client

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tasks = set()
    yield
    for task in list(app.state.tasks):
        task.cancel()
    await redis_client.aclose()
    await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
app.include_router(provider_router)


@app.get('/health')
async def healthcheck() -> dict[str, str]:
    return {'status': 'ok'}
