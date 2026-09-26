"""导入流程节点包。

本包职责只有两件事:
    1. 公开 API 再导出 (注册器 + 访问器);
    2. 显式 import 各节点模块 (顺序即流程图顺序), 触发 @register 自注册。

新增节点: 新建 node_xxx.py (用 @register / @node_log 堆叠装饰),
再在本文件补两行 (一条 import + 一条 __all__), 顺序可自行调整。
"""

from .registry import (
    NODES,
    NodeFunc,
    NodeMeta,
    get_cn,
    get_func,
    get_node,
    iter_nodes,
    node_names,
    register,
)
from .node_entry import node_entry
from .node_pdf_to_md import node_pdf_to_md
from .node_md_img import node_md_img
from .node_document_split import node_document_split
from .node_item_name_recognize import node_item_name_recognize
from .node_bge_embedding import node_bge_embedding
from .node_upsert_milvus import node_upsert_milvus

__all__ = [
    # 注册器 / 类型 / 访问器
    "NODES",
    "NodeMeta",
    "NodeFunc",
    "register",
    "get_node",
    "get_cn",
    "get_func",
    "iter_nodes",
    "node_names",
    # 节点函数
    "node_entry",
    "node_pdf_to_md",
    "node_md_img",
    "node_document_split",
    "node_item_name_recognize",
    "node_bge_embedding",
    "node_upsert_milvus",
]
