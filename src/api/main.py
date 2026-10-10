from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import __version__
from api.routers import chat, health, import_doc
from utils.logging_utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Shop Assistant API 启动 (version={})", __version__)
    yield
    logger.info("Shop Assistant API 关闭")


app = FastAPI(
    title="Shop Assistant API",
    description="前端经 FastAPI 调用 LangGraph 服务的网关",
    version=__version__,
    lifespan=lifespan,
)

# 开发阶段放开 CORS; 生产由 nginx 同源反代, 可收紧 allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由 (路由前缀统一为 /api, 与 Vite dev proxy 和 nginx 反代保持一致)
app.include_router(health.router)
app.include_router(import_doc.router)
app.include_router(chat.router)
