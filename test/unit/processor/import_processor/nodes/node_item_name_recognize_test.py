"""单元测试: src/processor/import_processor/nodes/node_item_name_recognize.py

被测对象:
    node_item_name_recognize    主体识别节点 (调用 LLM 归纳文档主体)

当前状态: 尚未实现, 仅透传 state (见源码 TODO)。

TODO: 实现后补充用例 (LLM 调用一律 mock)
    - 从文档靠前内容中识别主体, 写入 state["item_name"]
    - LLM 返回异常内容 / 超时时的兜底策略
    - 空文档 / 无标题时 item_name 的取值
"""
