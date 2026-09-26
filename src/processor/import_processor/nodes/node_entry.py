"""
    入口节点

    - 作用:
        1. 文件类型识别
        2. 状态数据补全
        3. 流程分支路由

    - 依赖状态数据:
        - task_id
        - origin_file_path

    - 更新状态数据:
        - doc_type

"""
from pathlib import Path

from common.enum.doc_type import DocType
from processor.import_processor.nodes.registry import register
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import logger, node_log
from utils.path_utils import get_project_root
from utils.task_utils import add_running_node, add_done_node

@register(cn="检查文件", description="识别文件类型、补全状态并路由")
@node_log()
def node_entry(state: ImportNodeState) -> ImportNodeState:
    add_running_node(state["task_id"], node_entry.__name__)

    # 1. 判断文件存在
    origin_file_path = Path(state["origin_file_path"])

    if not origin_file_path.exists():
        logger.warning(f"文件不存在: {origin_file_path}, 终止导入流程")
        add_done_node(state["task_id"], node_entry.__name__)
        return state

    # 2. 提取文件类型
    state["doc_type"] = DocType.from_filename(origin_file_path)

    if state["doc_type"] == DocType.UNKNOWN:
        logger.warning(f"未知文件类型: {origin_file_path}, 终止导入流程")
        add_done_node(state["task_id"], node_entry.__name__)
        return state

    if state["doc_type"] == DocType.MARKDOWN:
        state['markdown_file_path'] = origin_file_path

    add_done_node(state["task_id"], node_entry.__name__)
    return state


if __name__ == '__main__':
    from processor.import_processor.state import create_state

    # 单元测试：覆盖不支持类型、MD、PDF三种场景
    logger.info("===== 开始node_entry节点单元测试 =====")

    # 测试1: 不支持的TXT文件
    test_state1 = create_state(
        task_id="test_task_001",
        origin_file_path=get_project_root() / "test/test-data/test.txt"
    )
    state = node_entry(test_state1)
    logger.info(f"文件类型: {state['doc_type']}")

    # 测试2: MD文件
    test_state2 = create_state(
        task_id="test_task_002",
        origin_file_path=get_project_root() / "test/test-data/第一章-初识智能体.md"
    )
    state = node_entry(test_state2)
    logger.info(f"文件类型: {state['doc_type']}")

    # 测试3: PDF文件
    test_state3 = create_state(
        task_id="test_task_003",
        origin_file_path=get_project_root() / "test/test-data/entropy.pdf"
    )
    state = node_entry(test_state3)
    logger.info(f"文件类型: {state['doc_type']}")

    logger.info("===== 结束node_entry节点单元测试 =====")

