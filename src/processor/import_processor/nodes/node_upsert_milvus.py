from processor.import_processor.nodes.registry import register
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import node_log

@register(cn="写入向量库", description="将向量批量写入 Milvus")
@node_log()
def node_upsert_milvus(state: ImportNodeState) -> ImportNodeState:
    """
    存入向量库

    TODO:
    1. 连接 Milvus
    2. 根据 item_name 删除旧数据
    3. 批量插入新的向量数据
    """
    return state

if __name__ == "__main__":
    from processor.import_processor.state import get_default_state
    start_state = get_default_state()
    node_upsert_milvus(start_state)
