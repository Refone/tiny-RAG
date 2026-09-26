import json

from langgraph.constants import END
from langgraph.graph import StateGraph

from common.enum.doc_type import DocType
from processor.import_processor.nodes import *
from processor.import_processor.state import ImportNodeState, create_state
from utils.logging_utils import logger

workflow = StateGraph(ImportNodeState)

# 注册节点
workflow.add_node(node_entry)
workflow.add_node(node_pdf_to_md)
workflow.add_node(node_md_img)
workflow.add_node(node_document_split)
workflow.add_node(node_item_name_recognize)
workflow.add_node(node_bge_embedding)
workflow.add_node(node_upsert_milvus)


def file_type_router(state: ImportNodeState):
    """根据 doc_type 决定走 PDF 转换还是直接进入图片处理。"""
    doc_type = state.get("doc_type", DocType.UNKNOWN)
    if doc_type == DocType.PDF:
        return "node_pdf_to_md"
    if doc_type == DocType.MARKDOWN:
        return "node_md_img"
    logger.warning(f"不支持的文档类型: {doc_type!r}, 流程终止")
    return END


# 构建工作流
workflow.set_entry_point("node_entry")
workflow.add_conditional_edges(
    "node_entry",
    file_type_router,
    path_map={
        "node_pdf_to_md": "node_pdf_to_md",
        "node_md_img": "node_md_img",
        END: END,
    },
)
workflow.add_edge("node_pdf_to_md", "node_md_img")
workflow.add_edge("node_md_img", "node_document_split")
workflow.add_edge("node_document_split", "node_item_name_recognize")
workflow.add_edge("node_item_name_recognize", "node_bge_embedding")
workflow.add_edge("node_bge_embedding", "node_upsert_milvus")
workflow.add_edge("node_upsert_milvus", END)

import_processor = workflow.compile()


if __name__ == "__main__":
    logger.info("====== 开始测试 ======")

    keys = ("task_id", "doc_type", "origin_file_path", "file_title")

    for fname in ("xxx.pdf", "xxx.md", "xxx.docx"):
        initial_state = create_state(task_id=f"test-{fname}", origin_file_path=fname)
        final_state = import_processor.invoke(initial_state)
        logger.info(
            "最终状态: "
            + json.dumps(
                {k: final_state.get(k) for k in keys},
                indent=4,
                ensure_ascii=False,
            )
        )

    logger.info("====== 测试结束 ======")
