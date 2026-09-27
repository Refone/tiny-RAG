"""单元测试: src/processor/import_processor/nodes/node_bge_embedding.py

被测对象:
    node_bge_embedding    向量化节点 (BGE-M3 稠密 / 稀疏向量)

当前状态: 尚未实现, 仅透传 state (见源码 TODO)。

TODO: 实现后补充用例
    - mock 模型后校验 chunks 中写入的稠密 / 稀疏向量维度与数量一致
    - 模型加载失败时的异常处理
    - 空 chunks 不触发模型调用

说明: 真实加载 BGE-M3 的用例放 test/integration 并标记 @pytest.mark.integration。
"""
