"""入口节点: 校验文件存在性并识别文档类型, 补全状态字段。

依赖状态字段:
    - task_id           任务 ID (仅用于日志与任务追踪)
    - origin_file_path  原始文件路径

更新状态字段:
    - doc_type           识别出的文档类型 (DocType)
    - markdown_file_path 仅当 doc_type 为 MARKDOWN 时, 复用原文件路径

注意:
    本节点只负责「识别 + 补全」; 后续按 doc_type 的分支路由由
    main_graph.file_type_router 完成, 不在本节点内。
"""

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
        logger.warning(f"文件不存在: {origin_file_path}, 终止导入流程")
        return state

    # 2. 识别文档类型
    doc_type = DocType.from_filename(origin_file_path.name)
    state["doc_type"] = doc_type

    if doc_type == DocType.UNKNOWN:
        logger.warning(f"未知文件类型: {origin_file_path}, 终止导入流程")
        return state

    # 3. Markdown 无需转换, 直接复用原文件路径
    if doc_type == DocType.MARKDOWN:
        state["markdown_file_path"] = str(origin_file_path)

    return state


if __name__ == "__main__":
    from processor.import_processor.state import create_state
    from utils.path_utils import get_project_root

    # 冒烟测试: 三种样例文件各跑一次
    for task_id, name in (
        ("test_task_txt", "test.txt"),
        ("test_task_md", "第一章-初识智能体.md"),
        ("test_task_pdf", "entropy.pdf"),
    ):
        state = node_entry(
            create_state(
                task_id=task_id,
                origin_file_path=get_project_root() / "test/test-data" / name,
            )
        )
        logger.info(f"{name}: doc_type={state['doc_type']}")
