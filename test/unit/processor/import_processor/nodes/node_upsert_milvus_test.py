"""单元测试: src/processor/import_processor/nodes/node_upsert_milvus.py

被测对象:
    node_upsert_milvus    写入向量库节点 (按 item_name 删旧 + 批量插入)

当前状态: 尚未实现, 仅透传 state (见源码 TODO)。

TODO: 实现后补充用例 (Milvus 客户端一律 mock)
    - 按 item_name 先删后插的调用顺序与参数
    - 批量插入的分批逻辑 (超过单批上限时多次调用)
    - 连接失败 / 插入失败时的异常传播

说明: 真实连接 Milvus 的用例放 test/integration 并标记 @pytest.mark.integration。
"""
