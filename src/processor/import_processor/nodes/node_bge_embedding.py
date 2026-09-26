from processor.import_processor.nodes.registry import register
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import node_log

@register(cn="向量化", description="对 chunks 做 BGE 稠密/稀疏向量化")
@node_log()
def node_bge_embedding(state: ImportNodeState) -> ImportNodeState:
    """
    嵌入节点, 内容向量化

    TODO:
    1. 加载 BGE-M3 模型
    2. 计算每个 Chunk 文本的 稠密向量 和 稀疏向量
    3. 准备好写入 Milvus 数据库
    """
    return state
