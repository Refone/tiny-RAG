from utils.logging_util import node_log
from processor.import_processor.state import ImportGraphState

@node_log("node_entry")
def node_entry(state: ImportGraphState) -> ImportGraphState:
    """
    入口节点

    TODO:
    1. 接受文件路径.
    2. 判断文件类型
    3. 设置 state 中的路由标记 (is_md / is_pdf)
    """
    # HACK
    if "local_file_path" in state:
        path = state["local_file_path"]
        if path.endswith(".pdf"):
            state["is_pdf"] = True
        elif path.endswith(".md"):
            state["is_md"] = True

    return state