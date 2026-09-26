from utils.node_utils import trace_node
from processor.import_processor.state import ImportNodeState

@trace_node(desc="向量化")
def node_bge_embedding(state: ImportNodeState) -> ImportNodeState:
    """
    嵌入节点, 内容向量化

    TODO:
    1. 加载 BGE-M3 模型
    2. 计算每个 Chunk 文本的 稠密向量 和 稀疏向量
    3. 准备好写入 Milvus 数据库
    """
    return state
