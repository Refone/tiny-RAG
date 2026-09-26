import json

from langgraph.constants import END
from langgraph.graph import StateGraph

from common.enum.doc_type import DocType
from processor.import_processor.nodes import (
    node_bge_embedding,
    node_document_split,
    node_entry,
    node_item_name_recognize,
    node_md_img,
    node_pdf_to_md,
    node_upsert_milvus,
)
from processor.import_processor.state import ImportNodeState, create_state
from utils.logging_utils import logger

workflow = StateGraph(ImportNodeState)

# 注册节点:
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
        return node_pdf_to_md.__name__
    if doc_type == DocType.MARKDOWN:
        return node_md_img.__name__
    logger.warning(f"不支持的文档类型: {doc_type!r}, 流程终止")
    return END


# 构建工作流 (节点名统一取函数 __name__, 与注册时的规范名一致)
workflow.set_entry_point(node_entry.__name__)
workflow.add_conditional_edges(
    node_entry.__name__,
    file_type_router,
    path_map={
        node_pdf_to_md.__name__: node_pdf_to_md.__name__,
        node_md_img.__name__: node_md_img.__name__,
        END: END,
    },
)
workflow.add_edge(node_pdf_to_md.__name__, node_md_img.__name__)
workflow.add_edge(node_md_img.__name__, node_document_split.__name__)
workflow.add_edge(node_document_split.__name__, node_item_name_recognize.__name__)
workflow.add_edge(node_item_name_recognize.__name__, node_bge_embedding.__name__)
workflow.add_edge(node_bge_embedding.__name__, node_upsert_milvus.__name__)
workflow.add_edge(node_upsert_milvus.__name__, END)

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
