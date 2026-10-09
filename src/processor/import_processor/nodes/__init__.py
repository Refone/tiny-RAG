"""导入流程节点包。

本包职责:
    1. 显式 import 各节点模块 (顺序即流程图顺序), 触发模块加载;
    2. 把节点函数统一再导出, 供 main_graph 与外部引用。

新增节点: 新建 node_xxx.py (用 @trace_node 装饰),
再在本文件补两行 (一条 import + 一条 __all__), 顺序可自行调整。
"""

from .node_entry import node_entry
from .node_pdf_to_md import node_pdf_to_md
from .node_md_img import node_md_img
from .node_document_split import node_document_split
from .node_item_name_vect import node_item_name_vect
from .node_bge_embedding import node_bge_embedding
from .node_upsert_milvus import node_upsert_milvus

__all__ = [
    "node_entry",
    "node_pdf_to_md",
    "node_md_img",
    "node_document_split",
    "node_item_name_vect",
    "node_bge_embedding",
    "node_upsert_milvus",
]
