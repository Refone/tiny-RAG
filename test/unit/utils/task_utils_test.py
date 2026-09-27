"""单元测试: src/utils/task_utils.py

被测对象:
    add_running_node / add_done_node          节点列表追加 (按 task_id 去重)
    set_task_status / get_task_status         状态读写 (校验 TaskStatus)
    set_task_result / get_task_result         任务结果读写 (缺失时返回默认值)
    get_task_running_nodes / get_task_done_nodes
    clear_task                                幂等清空任务数据
    task_push_sse                             空实现, 待对接 SSE

用例由 src/utils/task_utils.py 的 __main__ 自测逻辑移植而来。

注意: 模块内的四个字典是进程级全局状态, 用例通过 autouse fixture 前后清空,
      保证彼此隔离; 需要断言「读操作不留残留」的用例直接检查这些私有字典。
"""

from __future__ import annotations

import pytest

from utils import task_utils
from utils.task_utils import (
    TaskStatus,
    add_done_node,
    add_running_node,
    clear_task,
    get_task_done_nodes,
    get_task_result,
    get_task_running_nodes,
    get_task_status,
    set_task_result,
    set_task_status,
)

# 本模块统一使用的任务 ID, 避免与其它模块/并行用例互相干扰
TASK_ID = "task-utils-unit-test"

# 全局字典名, 用于「读操作无副作用」断言 (用例隔离由 test/unit/conftest.py 统一负责)
_STORE_NAMES = (
    "_tasks_running_nodes",
    "_tasks_done_nodes",
    "_tasks_status",
    "_tasks_result",
)


# --------------------------------------------------------------------------- #
# TaskStatus 枚举
# --------------------------------------------------------------------------- #
def test_task_status_values():
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.COMPLETE == "complete"
    assert "failed" in TaskStatus
    assert "bogus" not in TaskStatus


# --------------------------------------------------------------------------- #
# 节点列表: 追加与去重
# --------------------------------------------------------------------------- #
def test_add_running_node_dedup():
    add_running_node(TASK_ID, "node_a")
    add_running_node(TASK_ID, "node_a")  # 重复, 应被去重
    add_running_node(TASK_ID, "node_b")
    assert get_task_running_nodes(TASK_ID) == ["node_a", "node_b"]


def test_add_done_node_dedup():
    add_done_node(TASK_ID, "node_a")
    add_done_node(TASK_ID, "node_a")  # 重复, 应被去重
    add_done_node(TASK_ID, "node_b")
    assert get_task_done_nodes(TASK_ID) == ["node_a", "node_b"]


def test_add_done_node_removes_from_running():
    """回归 U4: 完成后必须从「运行中」出队, 否则 running 与 done 完全重叠。"""
    add_running_node(TASK_ID, "node_a")
    add_running_node(TASK_ID, "node_b")

    add_done_node(TASK_ID, "node_a")

    assert get_task_running_nodes(TASK_ID) == ["node_b"]
    assert get_task_done_nodes(TASK_ID) == ["node_a"]


def test_add_done_node_for_untracked_task_creates_no_running_entry():
    """给从未运行过的任务记 done, 不应凭空建出「运行中」条目。"""
    add_done_node(TASK_ID, "node_a")

    assert get_task_done_nodes(TASK_ID) == ["node_a"]
    assert TASK_ID not in task_utils._tasks_running_nodes


# --------------------------------------------------------------------------- #
# 结果读写与默认值
# --------------------------------------------------------------------------- #
def test_result_get_set():
    assert get_task_result(TASK_ID, "k") == ""
    assert get_task_result(TASK_ID, "k", "dft") == "dft"
    set_task_result(TASK_ID, "k", "v1")
    set_task_result(TASK_ID, "k", "v2")  # 覆盖旧值
    assert get_task_result(TASK_ID, "k") == "v2"


# --------------------------------------------------------------------------- #
# 状态读写与默认值
# --------------------------------------------------------------------------- #
def test_status_get_set():
    assert get_task_status(TASK_ID) == ""  # 未设置时不抛 KeyError
    set_task_status(TASK_ID, TaskStatus.PROCESSING)
    assert get_task_status(TASK_ID) == "processing"


def test_status_invalid_raises():
    with pytest.raises(ValueError):
        set_task_status(TASK_ID, "not-a-status")


# --------------------------------------------------------------------------- #
# 读取不存在的任务: 返回空且无副作用
# --------------------------------------------------------------------------- #
def test_get_missing_task_no_side_effect():
    missing = "no-such-task"

    assert get_task_running_nodes(missing) == []
    assert get_task_done_nodes(missing) == []
    assert get_task_status(missing) == ""
    assert get_task_result(missing, "k") == ""

    # 读操作不应在字典里留下条目 (defaultdict 的坑) —— 直接检查私有字典
    for name in _STORE_NAMES:
        assert missing not in getattr(task_utils, name), f"{name} 被读操作写入了残留"


# --------------------------------------------------------------------------- #
# getter 返回副本, 避免调用方污染内部状态 (回归 U5)
# --------------------------------------------------------------------------- #
def test_getters_return_copies():
    add_running_node(TASK_ID, "node_a")
    add_done_node(TASK_ID, "node_b")

    running = get_task_running_nodes(TASK_ID)
    done = get_task_done_nodes(TASK_ID)
    running.append("外部改动")
    done.append("外部改动")

    # 返回值是副本, 改动它不影响内部状态
    assert get_task_running_nodes(TASK_ID) == ["node_a"]
    assert get_task_done_nodes(TASK_ID) == ["node_b"]
    assert task_utils._tasks_running_nodes[TASK_ID] == ["node_a"]


# --------------------------------------------------------------------------- #
# need_push 触发 SSE 推送
# --------------------------------------------------------------------------- #
def test_need_push_triggers_sse(monkeypatch):
    pushed: list[str] = []
    # 替换模块内引用, add_*_node 在调用时按全局名字查找, 因此 patch 生效
    monkeypatch.setattr(task_utils, "task_push_sse", pushed.append)

    add_running_node(TASK_ID, "node_a", need_push=True)
    add_done_node(TASK_ID, "node_a", need_push=True)
    add_running_node(TASK_ID, "node_b", need_push=False)  # 不推送

    assert pushed == [TASK_ID, TASK_ID]


# --------------------------------------------------------------------------- #
# clear_task 幂等
# --------------------------------------------------------------------------- #
def test_clear_task_idempotent():
    add_running_node(TASK_ID, "node_a")
    set_task_status(TASK_ID, TaskStatus.PENDING)
    set_task_result(TASK_ID, "k", "v")

    clear_task(TASK_ID)
    assert get_task_running_nodes(TASK_ID) == []
    assert get_task_status(TASK_ID) == ""
    assert get_task_result(TASK_ID, "k") == ""

    clear_task(TASK_ID)  # 再次清空不报错
    clear_task("never-exists")  # 清空不存在的任务不报错


# --------------------------------------------------------------------------- #
# defaultdict: 首次直接 append 不崩
# --------------------------------------------------------------------------- #
def test_defaultdict_first_append():
    task_utils._tasks_running_nodes["t2"].append("node_x")
    assert get_task_running_nodes("t2") == ["node_x"]


# --------------------------------------------------------------------------- #
# task_push_sse: 目前是空实现
# --------------------------------------------------------------------------- #
def test_task_push_sse_is_noop_for_now():
    """SSE 尚未对接, 当前空实现不应抛异常也不写状态 (对接后改成断言推送内容)。"""
    assert task_utils.task_push_sse(TASK_ID) is None
