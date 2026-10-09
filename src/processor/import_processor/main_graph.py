from langgraph.constants import END
from langgraph.graph import StateGraph
from processor.import_processor.state import ImportNodeState
from processor.import_processor.nodes import (
    node_bge_embedding,
    node_document_split,
    node_entry,
    node_item_name_vect,
    node_md_img,
    node_pdf_to_md,
    node_upsert_milvus,
)

workflow = StateGraph(ImportNodeState)

# 注册节点:
workflow.add_node(node_entry)
workflow.add_node(node_pdf_to_md)
workflow.add_node(node_md_img)
workflow.add_node(node_document_split)
workflow.add_node(node_item_name_vect)
workflow.add_node(node_bge_embedding)
workflow.add_node(node_upsert_milvus)


def file_type_router(state: ImportNodeState):
    """根据 doc_type 决定走 PDF 转换还是直接进入图片处理。"""
    if state.get("markdown_file_path"):
        return node_md_img.__name__
    else:
        return node_pdf_to_md.__name__


# 构建工作流 (节点名统一取函数 __name__, 与注册时的规范名一致)
workflow.set_entry_point(node_entry.__name__)
workflow.add_conditional_edges(
    node_entry.__name__,
    file_type_router,
    path_map={
        node_pdf_to_md.__name__: node_pdf_to_md.__name__,
        node_md_img.__name__: node_md_img.__name__,
    },
)
workflow.add_edge(node_pdf_to_md.__name__, node_md_img.__name__)
workflow.add_edge(node_md_img.__name__, node_document_split.__name__)
workflow.add_edge(node_document_split.__name__, node_item_name_vect.__name__)
workflow.add_edge(node_item_name_vect.__name__, node_bge_embedding.__name__)
workflow.add_edge(node_bge_embedding.__name__, node_upsert_milvus.__name__)
workflow.add_edge(node_upsert_milvus.__name__, END)

import_processor = workflow.compile()

if __name__ == "__main__":
    from utils import task_utils
    from processor.import_processor.state import create_state
    from utils.logging_utils import logger
    from utils.path_utils import PROJECT_ROOT
    from rich import print as rprint

    print(import_processor.get_graph().draw_ascii())

    task_id = "import-pdf-test"
    origin_file_path = PROJECT_ROOT / "asset/hak180产品安全手册.pdf"
    # origin_file_path = PROJECT_ROOT / "asset/万用表RS-12的使用.pdf"

    task_utils.clear_task(task_id)
    initial_state = create_state(
        task_id=task_id,
        origin_file_path=str(origin_file_path),
    )

    end_state = import_processor.invoke(initial_state)

    logger.complete()

    rprint(task_utils.get_task_done_nodes(task_id))
    rprint(end_state)
