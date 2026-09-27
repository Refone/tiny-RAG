"""单元测试: src/processor/import_processor/nodes/node_document_split.py

被测对象:
    node_document_split    文档切分节点 (Markdown 标题递归切分 + 生成 Chunk)

当前状态: 尚未实现, 仅透传 state (见源码 TODO)。

TODO: 实现后补充用例
    - 基于标题层级递归切分, 校验 chunk 数量与边界
    - 超长段落触发二次切分
    - chunk 携带 Metadata (来源文件 / 标题路径 / item_name)
    - 空文档 / 无标题文档不抛异常
"""
