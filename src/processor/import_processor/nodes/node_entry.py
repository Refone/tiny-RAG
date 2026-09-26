from pathlib import Path

from common.enum.doc_type import DocType
from processor.import_processor.nodes.registry import register
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import logger, node_log
from utils.task_utils import add_running_node

@register(cn="检查文件", description="识别文件类型、补全状态并路由")
@node_log()
def node_entry(state: ImportNodeState) -> ImportNodeState:
    """
    入口节点

    1. 文件类型识别
    2. 状态数据补全
    3. 流程分支路由
    """

    # 1. 任务开始 (任务管理里只存「规范名」, 展示层用 get_cn 再映射成中文)
    add_running_node(state["task_id"], node_entry.__name__)


    return state


if __name__ == '__main__':
    from processor.import_processor.state import get_default_state

    logger.info("===== node_entry 单元测试 =====")

    for fname in ("a.pdf", "b.MD", "c.unknown"):
        s = get_default_state()
        s["origin_file_path"] = fname
        node_entry(s)
        logger.info(f"结果: {fname!r} -> {s['doc_type']!r}, file_title={s['file_title']!r}")

    logger.info("===== node_entry 单元测试结束 =====")
