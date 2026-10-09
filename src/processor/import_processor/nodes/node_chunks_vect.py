from utils.node_utils import trace_node
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import logger


@trace_node(desc="向量化")
def node_chunks_vect(state: ImportNodeState) -> ImportNodeState:
    """
    嵌入节点, 内容向量化
    """
    logger.info("Executing node_chunks_vect")
    return state
