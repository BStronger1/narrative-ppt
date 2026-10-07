from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.spa import SPAStaticFiles
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.paths import REPO_ROOT
from app.core.queue import close_arq_pool
from app.core.redis import close_redis, get_redis


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 启动时预热 Redis 连接池；退出时关闭，避免连接泄漏
    get_redis()
    yield
    await close_arq_pool()
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AI PPT生成 API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    web_dist = REPO_ROOT / "frontend" / "dist"
    if web_dist.is_dir():
        app.mount("/", SPAStaticFiles(directory=web_dist, html=True), name="web")
    return app


app = create_app()
