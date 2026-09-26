from pathlib import Path

from common.enum.doc_type import DocType
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import node_log, logger

@node_log("node_entry")
def node_entry(state: ImportNodeState) -> ImportNodeState:
    """
    入口节点

    1. 文件类型识别
    2. 状态数据补全
    3. 流程分支路由
    """
    # HACK
    origin = state.get("origin_file_path", "").strip()
    if not origin:
        logger.warning("origin_file_path 为空, 无法判定文件类型, 流程将直接结束")
        return state

    state["doc_type"] = DocType.from_filename(origin)
    if not state.get("file_title"):
        state["file_title"] = Path(origin).stem
    logger.info(f"文件类型判定: {origin!r} -> {state['doc_type']}")

    # 1. 接收状态

    # 2. 记录开始

    # 3. 读取输入路径并校验

    # 4. 判断文件类型并更新对应状态

    # 5. 提取文件标题

    # 6. 记录完成

    # 7. 返回最新状态

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
