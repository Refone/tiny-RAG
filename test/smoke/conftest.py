"""test/smoke 共享 fixture 与 hook。

两个职责:
1. clean_task_store: 冒烟测试会真正 invoke 导入流程图, 每个节点被 @trace_node
   包装, 运行时写入 task_utils 的进程级全局字典 (running/done/status/result)。
   在每个用例前后统一清空, 保证用例之间互不污染, 也让「断言节点链」只读到
   当前用例产生的结果。
2. pytest_runtest_call hook: 用 -s 跑冒烟时, 各节点的 loguru 日志直接打到
   stdout, 相邻用例的日志会连在一起; 该 hook 用横幅把每个用例的日志包裹起来,
   并在用例体跑完后立刻 flush loguru 的异步队列, 让「结束横幅」一定落在本用例
   所有日志之后、pytest 进度字符 ('.'/PASSED) 之前, 避免日志与进度字符交错。
"""

from __future__ import annotations

import pytest

from utils import task_utils
from utils.logging_utils import logger

# task_utils 内部的全局字典名
TASK_STORE_NAMES = (
    "_tasks_running_nodes",
    "_tasks_done_nodes",
    "_tasks_status",
    "_tasks_result",
)

_SEP = "=" * 80


@pytest.fixture(autouse=True)
def clean_task_store():
    """清空 task_utils 的全局任务字典, 用例前后各执行一次。"""
    for name in TASK_STORE_NAMES:
        getattr(task_utils, name).clear()
    yield
    for name in TASK_STORE_NAMES:
        getattr(task_utils, name).clear()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    """用横幅分隔每个用例"""
    print(f"\n{_SEP}\n▶ 用例开始: {item.nodeid}\n{_SEP}", flush=True)
    yield               # 执行流返还给测试用例
    logger.complete()   # flush loguru 异步日志
    print(f"{_SEP}\n■ 用例结束: {item.name}\n{_SEP}\n", flush=True)
