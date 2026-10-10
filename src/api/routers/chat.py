from fastapi import APIRouter, HTTPException

from api.schemas.chat import ChatRequest, ChatResponse
from service.chat_service import achat

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """聊天端点。query_processor 图尚未落地, 暂返回 501。"""
    try:
        reply = await achat(request.message)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))
    return ChatResponse(reply=reply)
