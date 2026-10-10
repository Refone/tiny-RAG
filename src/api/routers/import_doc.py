import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from api.schemas.import_doc import ImportResponse, ImportStatusResponse
from service.import_service import arun_import
from utils import task_utils
from utils.path_utils import PROJECT_ROOT

router = APIRouter(prefix="/api/import", tags=["import"])

# 上传暂存目录 (生产建议换成 MinIO / 共享卷, 避免多副本写本地盘不一致)
UPLOAD_DIR = PROJECT_ROOT / "output" / "uploads"

# 后台任务强引用集合: 防止 asyncio.Task 被垃圾回收提前取消
_background_tasks: set[asyncio.Task] = set()


@router.post("", response_model=ImportResponse, status_code=202)
async def import_document(file: UploadFile = File(...)) -> ImportResponse:
    """接收文件、落盘、后台启动 LangGraph 导入图, 立即返回任务 ID。

    导入是长任务 (MinerU / VLM / Milvus embedding), 不阻塞 HTTP 请求;
    进度经 GET /api/import/{task_id} 查询。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")

    task_id = uuid.uuid4().hex
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f"{task_id}_{Path(file.filename).name}"
    dest.write_bytes(await file.read())

    task = asyncio.create_task(
        arun_import(task_id=task_id, origin_file_path=str(dest))
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return ImportResponse(
        task_id=task_id,
        status=task_utils.TaskStatus.PENDING.value,
    )


@router.get("/{task_id}", response_model=ImportStatusResponse)
async def import_status(task_id: str) -> ImportStatusResponse:
    """查询任务进度 (状态 / 运行中节点 / 已完成节点 / 结果)。"""
    status = task_utils.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    return ImportStatusResponse(
        task_id=task_id,
        status=status,
        running_nodes=task_utils.get_task_running_nodes(task_id),
        done_nodes=task_utils.get_task_done_nodes(task_id),
        result=task_utils.get_task_results(task_id),
    )
