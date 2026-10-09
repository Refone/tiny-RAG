import json
import copy
from typing import TypedDict

from utils.path_utils import PROJECT_ROOT


class ImportNodeState(TypedDict):
    """
    导入图状态

    Tips:
    考虑到 Graph State 可能需要做 持久化 和 跨平台,
    故最好使用原生数据结构, 以便正常序列化。
    例如路径保持 str, 而非 Path,
    """

    # 任务 ID
    task_id: str

    # 原始文件路径, 不确定文件格式
    origin_file_path: str

    # (转换后的) markdown 文件路径
    markdown_file_path: str

    # 文件名 (不含后缀)
    file_title: str

    # 文档切分后的 JSON 文件路径 (node_document_split 产出)
    chunks_json_path: str

    # 文档主体识别结果, 如 "iPhone 13" (node_item_name_vect 产出)
    item_name: str


_DEFAULT_STATE: ImportNodeState = {
    "task_id": "",
    "origin_file_path": "",
    "markdown_file_path": "",
    "file_title": "",
    "item_name": "",
    "chunks_json_path": "",
}


def create_state(**state_dict) -> ImportNodeState:
    """
    根据传入字典，创建一个新的导入节点状态
    """

    state = copy.deepcopy(_DEFAULT_STATE)
    state.update(state_dict)
    return state


def get_default_state() -> ImportNodeState:
    """
    获取默认的导入节点状态
    """

    return copy.deepcopy(_DEFAULT_STATE)


def save_state(state: ImportNodeState, file_path: str) -> None:
    """
    将当前状态保存到指定文件路径
    """

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=4)


def load_state(file_path: str) -> ImportNodeState:
    """
    从指定文件路径加载状态
    """

    with open(file_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    return state


if __name__ == "__main__":
    from rich import print as rprint

    state = create_state(
        task_id="test-task-001",
        origin_file_path=str(PROJECT_ROOT / "asset/万用表RS-12的使用.pdf"),
    )

    rprint(state)
    save_state(state, str(PROJECT_ROOT / "output/tmp/state_test.json"))
