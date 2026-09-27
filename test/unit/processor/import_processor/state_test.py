"""单元测试: src/processor/import_processor/state.py

被测对象:
    create_state          创建导入图状态 (校验字段合法性)
    get_default_state     返回默认状态副本
    ImportNodeState       导入流程唯一事实来源 (TypedDict)

TODO: 补充用例
    - 默认状态包含全部已声明字段, 且 doc_type=DocType.UNKNOWN, chunks=[]
    - 传入未声明字段抛 KeyError (防止 LangGraph 静默丢字段)
    - 返回值与内部默认状态不共享可变对象 (chunks 深拷贝)
    - 多次调用 get_default_state 互不影响 (改动其一不影响其二)
    - create_state 传入的字段能正确覆盖默认值
"""
