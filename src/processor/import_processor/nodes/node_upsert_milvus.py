from common.logging.logger import node_log
from processor.import_processor.state import ImportGraphState

@node_log("node_import_milvus")
def node_upsert_milvus(state: ImportGraphState) -> ImportGraphState:
    """
    存入向量库

    TODO:
    1. 连接 Milvus
    2. 根据 item_name 删除旧数据
    3. 批量插入新的向量数据
    """
    return state