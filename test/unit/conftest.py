"""test/unit 共享 fixture。

单元测试本身多是纯函数, 但 `utils/task_utils.py` 用四个模块级字典保存任务状态,
属于进程级全局状态; 只测 utils 与 processor 的节点时都会碰到它。
这里统一在用例前后清空, 保证用例之间互不污染, 各测试模块不必各自实现一遍。
"""

from __future__ import annotations

import pytest

from utils import task_utils

# task_utils 内部的全局字典名 (隔离 fixture 与断言都以此为准)
TASK_STORE_NAMES = (
    "_tasks_running_nodes",
    "_tasks_done_nodes",
    "_tasks_status",
    "_tasks_result",
)


@pytest.fixture(autouse=True)
def clean_task_store():
    """清空 task_utils 的全局任务字典, 用例前后各执行一次。"""
    for name in TASK_STORE_NAMES:
        getattr(task_utils, name).clear()
    yield
    for name in TASK_STORE_NAMES:
        getattr(task_utils, name).clear()
