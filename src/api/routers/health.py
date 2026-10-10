from fastapi import APIRouter

from api import __version__

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health() -> dict:
    """健康检查, 同时用于 docker-compose healthcheck。"""
    return {"status": "ok", "version": __version__}
