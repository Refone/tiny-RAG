from common.logging.logger import node_log
from processor.import_processor.state import ImportGraphState

@node_log("node_pdf_to_md")
def node_pdf_to_md(state: ImportGraphState) -> ImportGraphState:
    """
    PDF 转 Markdown 节点

    TODO:
    1. 调用 MinerU (magic-pdf) 工具
    2. 讲 PDF 保存为 Markdown 格式
    3. 将结果保存到 state["md_content"]
    """
    return state