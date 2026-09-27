"""单元测试: src/utils/task_utils.py

被测对象:
    add_running_node / add_done_node          节点列表追加 (按 task_id 去重)
    set_task_status / get_task_status         状态读写 (校验 TaskStatus)
    set_task_result / get_task_result         任务结果读写 (缺失时返回默认值)
    get_task_running_nodes / get_task_done_nodes
    clear_task                                幂等清空任务数据
    task_push_sse                             空实现, 待对接 SSE

TODO: 补充用例
    - 重复 add 同一节点只保留一份, 且保持插入顺序
    - set_task_status 传非法值抛 ValueError, 传 TaskStatus 合法值可读写
    - 未设置状态 / 不存在的 task_id 返回 "" 或空列表 (无副作用)
    - set_task_result 覆盖同名 key; get_task_result 缺失时返回 default
    - clear_task 后各 getter 恢复默认值, 对不存在的 task_id 不报错

注意: 模块级字典是全局状态, 用例需用 clear_task 或唯一 task_id 做隔离。
"""
