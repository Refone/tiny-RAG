from utils.node_utils import trace_node
from processor.import_processor.state import ImportNodeState

@trace_node(desc="主体识别")
def node_item_name_recognize(state: ImportNodeState) -> ImportNodeState:
    """
    主体识别节点

    TODO:
    1. 取文档标题等靠前内容.
    2. 调用 LLM 识别归纳整片文档内容主体(如 "IPhone 13")
    3. 存入 state["item_name"] 用于后续数据查询提速
    """
    return state
