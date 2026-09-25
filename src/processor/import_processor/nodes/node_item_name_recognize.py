from utils.logging_util import node_log
from processor.import_processor.state import ImportGraphState

@node_log("node_item_name_recognize")
def node_item_name_recognize(state: ImportGraphState) -> ImportGraphState:
    """
    主体识别节点

    TODO:
    1. 取文档标题等靠前内容.
    2. 调用 LLM 识别归纳整片文档内容主体(如 "IPhone 13")
    3. 存入 state["item_name"] 用于后续数据查询提速
    """
    return state