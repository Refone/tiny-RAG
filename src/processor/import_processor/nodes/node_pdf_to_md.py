from processor.import_processor.nodes.registry import register
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import node_log

@register(cn="PDF 转 Markdown", description="调用 MinerU 将 PDF 转为 Markdown")
@node_log()
def node_pdf_to_md(state: ImportNodeState) -> ImportNodeState:
    """
    PDF 转 Markdown 节点

    TODO:
    1. 调用 MinerU (magic-pdf) 工具
    2. 讲 PDF 保存为 Markdown 格式
    3. 将结果保存到 state["md_content"]
    """
    return state
