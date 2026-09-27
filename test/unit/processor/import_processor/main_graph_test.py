"""单元测试: src/processor/import_processor/main_graph.py

被测对象:
    file_type_router    按 doc_type 路由: PDF -> node_pdf_to_md, MD -> node_md_img, 其他 -> END
    import_processor    编译后的导入流程图

TODO: 补充用例
    - DocType.PDF / DocType.MARKDOWN / DocType.UNKNOWN 三种入参的返回节点名
    - state 缺少 doc_type 时回退 DocType.UNKNOWN 并返回 END
    - 图结构完整性: 入口节点、各节点注册名与条件边 path_map 一致

说明: 只测路由函数与图结构, 不真正 invoke (节点实现依赖外部服务)。
"""
