from utils.logging_util import node_log
from processor.import_processor.state import ImportNodeState

@node_log("node_document_split")
def node_document_split(state: ImportNodeState) -> ImportNodeState:
    """
    文档切分节点

    TODO:
    1. 基于 Markdown 标题层级进行递归切分
    2. 对仍然过长的段落进行二次切分
    3. 生成包含 Metadata 的 Chunk 列表
    """
    return state