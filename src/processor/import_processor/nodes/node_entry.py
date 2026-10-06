from pathlib import Path

from common.enum.doc_type import DocType
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import logger
from utils.node_utils import trace_node

@trace_node(desc="入口节点")
def node_entry(state: ImportNodeState) -> ImportNodeState:
    """识别文件类型并补全状态字段; 文件缺失或类型不受支持时原样返回。"""
    origin_file_path = Path(state["origin_file_path"])

    # 1. 文件存在性校验
    if not origin_file_path.exists():
        raise FileNotFoundError(f"文件不存在: {origin_file_path}, 流程终止")

    # 2. 识别文档类型
    doc_type = DocType.from_filename(origin_file_path.name)
    if doc_type == DocType.UNKNOWN:
        raise ValueError(f"未知文件类型: {origin_file_path}, 流程终止")

    # 3. 更新 state 对应字段
    state["file_title"] = origin_file_path.stem

    if doc_type == DocType.MARKDOWN:
        state["markdown_file_path"] = str(origin_file_path)

    logger.info(f"文件校验通过: {origin_file_path} 文件类型: {DocType.to_str(doc_type)}")

    return state


if __name__ == "__main__":
    from processor.import_processor.state import create_state, save_state
    from utils.path_utils import PROJECT_ROOT
    from rich import print as rprint

    start1 = create_state(
        task_id="test_task_start",
        origin_file_path=str(PROJECT_ROOT / "asset/hello-agent.md"),
    )
    end1 = node_entry(start1)
    rprint(end1)

    try:
        start2 = create_state(
            task_id="test_task_start",
            origin_file_path=str(PROJECT_ROOT / "asset/test.txt"),
        )
        end2 = node_entry(start2)
        rprint(end2)
    except Exception as e:
        logger.error(f"流程执行出错: {e}")

    start_state = create_state(
        task_id="test_task_start",
        origin_file_path=str(PROJECT_ROOT / "asset/万用表RS-12的使用.pdf"),
    )
    end_state = node_entry(start_state)
    rprint(end_state)

    save_state(end_state, str(PROJECT_ROOT / "output/tmp/import_01_entry.json"))
    logger.info(f"状态已保存: {PROJECT_ROOT / 'output/tmp/import_01_entry.json'}")