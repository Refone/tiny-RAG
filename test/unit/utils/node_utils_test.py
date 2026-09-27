"""单元测试: src/utils/node_utils.py

被测对象:
    node_log     节点日志装饰器 (签名 func(state, ...))
    step_log     步骤日志装饰器 (签名 func(*args, **kwargs))
    trace_node   节点统一装饰器 (日志 + 任务追踪)

TODO: 补充用例
    - functools.wraps 生效: 保留原函数的 __name__ / __doc__
    - 正常返回时结果原样透传, 并把节点写入「已完成」列表
    - 被装饰函数抛异常时记录 exception 且原样向上抛出
    - state 缺少 task_id 时回退为 "-", 不抛 KeyError
    - step_log 支持普通函数 (无 state) 的调用

注意: trace_node 会写入 task_utils 的全局字典, 用例结束需清理 (clear_task)。
"""
