from typing import Dict, List

from pydantic import BaseModel


class ImportResponse(BaseModel):
    """POST /api/import 的响应: 提交成功后立即返回任务 ID。"""

    task_id: str
    status: str


class ImportStatusResponse(BaseModel):
    """GET /api/import/{task_id} 的响应: 任务进度快照。"""

    task_id: str
    status: str
    running_nodes: List[str]
    done_nodes: List[str]
    result: Dict[str, str]
