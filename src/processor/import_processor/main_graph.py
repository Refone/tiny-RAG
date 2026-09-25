import json

from processor.import_processor.nodes import *
from langgraph.constants import END
from langgraph.graph import StateGraph
from processor.import_processor.state import ImportGraphState, create_default_state
from utils.logging_util import logger

workflow = StateGraph(ImportGraphState)

# 注册节点
workflow.add_node(node_entry)
workflow.add_node(node_pdf_to_md)
workflow.add_node(node_md_img)
workflow.add_node(node_document_split)
workflow.add_node(node_item_name_recognize)
workflow.add_node(node_bge_embedding)
workflow.add_node(node_upsert_milvus)

def file_type_router(state: ImportGraphState):
    if state.get("is_pdf"):
        return "node_pdf_to_md"
    elif state.get("is_md"):
        return "node_md_img"
    else:
        return END

# 构建工作流
workflow.set_entry_point("node_entry")
workflow.add_conditional_edges("node_entry",
                               file_type_router,
                               path_map={
                                   "node_md_img": "node_md_img",
                                   "node_pdf_to_md": "node_pdf_to_md",
                                   END: END
                               })
workflow.add_edge("node_pdf_to_md", "node_md_img")
workflow.add_edge("node_md_img", "node_document_split")
workflow.add_edge("node_document_split", "node_item_name_recognize")
workflow.add_edge("node_item_name_recognize", "node_bge_embedding")
workflow.add_edge("node_bge_embedding", "node_upsert_milvus")
workflow.add_edge("node_upsert_milvus", END)

import_processor = workflow.compile()

if __name__ == "__main__":
    logger.info("====== 开始测试 ======")

    initial_state = create_default_state(local_file_path="xxx.docs")
    final_state = import_processor.invoke(initial_state)
    logger.info(
        f"最终状态: {json.dumps(
            {k: final_state.get(k) for k in ('is_md', 'is_pdf', 'local_file_path')},
            indent=4,
            ensure_ascii=False,
        )}"
    )

    initial_state = create_default_state(local_file_path="xxx.pdf")
    final_state = import_processor.invoke(initial_state)
    logger.info(
        f"最终状态: {json.dumps(
            {k: final_state.get(k) for k in ('is_md', 'is_pdf', 'local_file_path')},
            indent=4,
            ensure_ascii=False,
        )}"
    )

    initial_state = create_default_state(local_file_path="xxx.md")
    final_state = import_processor.invoke(initial_state)
    logger.info(
        f"最终状态: {json.dumps(
            {k: final_state.get(k) for k in ('is_md', 'is_pdf', 'local_file_path')},
            indent=4,
            ensure_ascii=False,
        )}"
    )

    # logger.info("图结构:")
    # import_processor.get_graph().print_ascii()

    logger.info("====== 测试结束 ======")