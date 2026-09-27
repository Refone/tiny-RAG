"""单元测试: src/utils/node_utils.py

被测对象:
    node_log     节点日志装饰器 (签名 func(state, ...), 记开始/完成/异常)
    step_log     步骤日志装饰器 (签名 func(*args, **kwargs))
    _task_trace  任务追踪包装: 开始记 running, 结束(含异常)记 done
    trace_node   节点统一装饰器, 组合 node_log + _task_trace

说明:
    - 装饰器在「装饰时」就会调用 `logger.bind(...)` 绑定文件/函数/行号, 因此
      要观察日志行为的用例必须先把 `node_utils.logger` 换成 spy, 再在用例内定义函数。
    - 任务追踪写入 task_utils 的全局字典, 隔离由 test/unit/conftest.py 的
      clean_task_store 统一负责。
"""

from __future__ import annotations

import pytest

from utils import node_utils, task_utils
from utils.task_utils import get_task_done_nodes, get_task_running_nodes

TASK_ID = "node-utils-unit-test"


class _LoggerSpy:
    """loguru logger 替身: 记录 bind / opt / info / error 调用。"""

    def __init__(self) -> None:
        self.binds: list[dict] = []
        self.infos: list[str] = []
        self.errors: list[str] = []
        self.exception_flags: list[bool] = []

    def bind(self, **kwargs):
        self.binds.append(kwargs)
        return self

    def opt(self, **kwargs):
        self.exception_flags.append(bool(kwargs.get("exception")))
        return self

    def info(self, message, *args, **kwargs) -> None:
        self.infos.append(message)

    def error(self, message, *args, **kwargs) -> None:
        self.errors.append(message)


# --------------------------------------------------------------------------- #
# node_log: 元信息与返回值
# --------------------------------------------------------------------------- #
def test_node_log_keeps_function_metadata(monkeypatch):
    monkeypatch.setattr(node_utils, "logger", _LoggerSpy())

    @node_utils.node_log("自增")
    def increase(state):
        """把 state['a'] 加一。"""
        state["a"] += 1
        return state

    assert increase.__name__ == "increase"
    assert increase.__doc__ == "把 state['a'] 加一。"
    # functools.wraps 会挂上 __wrapped__ 指向原函数
    assert increase.__wrapped__.__name__ == "increase"


def test_node_log_returns_result_and_mutates_state(monkeypatch):
    monkeypatch.setattr(node_utils, "logger", _LoggerSpy())

    @node_utils.node_log("自增")
    def increase(state):
        state["a"] += 1
        return state

    state = {"task_id": "t1", "a": 0}
    result = increase(state)

    assert result is state
    assert state["a"] == 1


def test_node_log_binds_real_identity(monkeypatch):
    spy = _LoggerSpy()
    monkeypatch.setattr(node_utils, "logger", spy)

    @node_utils.node_log("自增")
    def target(state):
        return state

    original = target.__wrapped__
    assert spy.binds == [
        {
            "_file": "node_utils_test.py",
            "_function": "target",
            "_line": original.__code__.co_firstlineno + 1,
        }
    ]


# --------------------------------------------------------------------------- #
# node_log: 日志内容
# --------------------------------------------------------------------------- #
def test_node_log_logs_start_and_finish(monkeypatch):
    spy = _LoggerSpy()
    monkeypatch.setattr(node_utils, "logger", spy)

    @node_utils.node_log("入口节点")
    def target(state):
        return state

    target({"task_id": "task-1"})

    assert spy.infos[0] == "节点开始 [入口节点] <task_id = task-1>"
    assert spy.infos[1].startswith("节点完成 [入口节点] <task_id = task-1>, 耗时=")
    assert spy.errors == []


def test_node_log_description_defaults_to_function_name(monkeypatch):
    spy = _LoggerSpy()
    monkeypatch.setattr(node_utils, "logger", spy)

    @node_utils.node_log()
    def target(state):
        return state

    target({"task_id": "task-1"})

    assert spy.infos[0] == "节点开始 [target] <task_id = task-1>"


def test_node_log_falls_back_when_task_id_missing(monkeypatch):
    spy = _LoggerSpy()
    monkeypatch.setattr(node_utils, "logger", spy)

    @node_utils.node_log("无 task_id")
    def target(state):
        return state

    # 缺 task_id 时用 "-" 兜底, 不抛 KeyError
    target({})

    assert spy.infos[0] == "节点开始 [无 task_id] <task_id = ->"


def test_node_log_reraises_and_logs_exception(monkeypatch):
    spy = _LoggerSpy()
    monkeypatch.setattr(node_utils, "logger", spy)

    @node_utils.node_log("会炸的节点")
    def boom(state):
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        boom({"task_id": "t1"})

    assert len(spy.infos) == 1  # 只有「开始」, 没有「完成」
    assert spy.errors[0].startswith("节点异常 [会炸的节点]")
    assert spy.exception_flags == [True]  # opt(exception=True) 才会带堆栈


# --------------------------------------------------------------------------- #
# step_log: 普通函数 (无 state)
# --------------------------------------------------------------------------- #
def test_step_log_works_with_plain_function(monkeypatch):
    spy = _LoggerSpy()
    monkeypatch.setattr(node_utils, "logger", spy)

    @node_utils.step_log("相加")
    def add(a, b):
        """两个数相加。"""
        return a + b

    assert add(2, 3) == 5
    assert add.__name__ == "add"
    assert add.__doc__ == "两个数相加。"
    assert spy.infos[0] == "步骤开始 [相加]"
    assert spy.infos[1].startswith("步骤完成 [相加], 耗时=")


def test_step_log_reraises_and_logs_exception(monkeypatch):
    spy = _LoggerSpy()
    monkeypatch.setattr(node_utils, "logger", spy)

    @node_utils.step_log()
    def boom(value):
        raise RuntimeError("step boom")

    with pytest.raises(RuntimeError, match="step boom"):
        boom(1)

    assert spy.errors[0].startswith("步骤异常 [boom]")
    assert spy.exception_flags == [True]


# --------------------------------------------------------------------------- #
# _task_trace / trace_node: 任务追踪
# --------------------------------------------------------------------------- #
def test_task_trace_uses_given_node_name():
    @node_utils._task_trace("自定义节点名")
    def target(state):
        return state

    target({"task_id": TASK_ID})

    assert get_task_running_nodes(TASK_ID) == []  # 完成后已出队
    assert get_task_done_nodes(TASK_ID) == ["自定义节点名"]


def test_trace_node_records_running_then_done():
    seen: dict[str, list[str]] = {}

    @node_utils.trace_node(desc="演示节点")
    def demo_node(state):
        seen["running_in_body"] = list(get_task_running_nodes(TASK_ID))
        seen["done_in_body"] = list(get_task_done_nodes(TASK_ID))
        return state

    state = {"task_id": TASK_ID}
    assert demo_node(state) is state

    # 函数体执行时: 已记 running, 还没记 done
    assert seen["running_in_body"] == ["demo_node"]
    assert seen["done_in_body"] == []
    # 节点标识取函数名 (与 LangGraph 注册名一致), 而不是 desc
    assert get_task_done_nodes(TASK_ID) == ["demo_node"]
    # 完成后从 running 出队 (U4): running 只表示「进行中」
    assert get_task_running_nodes(TASK_ID) == []


def test_trace_node_does_not_push_by_default(monkeypatch):
    """need_push 默认 False: 不显式开启就不推送, 把开关的决定权留给装饰器使用方。"""
    pushed: list[str] = []
    monkeypatch.setattr(task_utils, "task_push_sse", pushed.append)

    @node_utils.trace_node(desc="探针节点")
    def probe_node(state):
        return state

    probe_node({"task_id": TASK_ID})

    assert pushed == []
    assert get_task_done_nodes(TASK_ID) == ["probe_node"]  # 任务追踪本身照旧


def test_trace_node_pushes_when_need_push_enabled(monkeypatch):
    """显式 need_push=True 时, running / done 两次状态变化各推送一次。"""
    pushed: list[str] = []
    monkeypatch.setattr(task_utils, "task_push_sse", pushed.append)

    @node_utils.trace_node(desc="探针节点", need_push=True)
    def probe_node(state):
        return state

    probe_node({"task_id": TASK_ID})

    assert pushed == [TASK_ID, TASK_ID]


def test_trace_node_need_push_is_inert_without_task_trace(monkeypatch):
    """task_trace=False 时不做任务追踪, need_push 自然也不会产生推送。"""
    pushed: list[str] = []
    monkeypatch.setattr(task_utils, "task_push_sse", pushed.append)

    @node_utils.trace_node(desc="只记日志", task_trace=False, need_push=True)
    def only_log(state):
        return state

    only_log({"task_id": TASK_ID})

    assert pushed == []


def test_trace_node_records_done_on_exception():
    """异常路径也记 done —— 这是 U2 确认保留的**刻意行为**, 不是待修缺陷。

    代价: 成功与失败在任务列表里无法区分, `TaskStatus.FAILED` 目前无人写入。
    若以后要区分, 改 `_task_trace` 的 finally 分支并在 task_utils 增加 failed 记录。
    """

    @node_utils.trace_node(desc="会抛异常的节点")
    def bad_node(state):
        raise ValueError("node boom")

    with pytest.raises(ValueError, match="node boom"):
        bad_node({"task_id": TASK_ID})

    # finally 保证异常路径也会记 done
    assert get_task_done_nodes(TASK_ID) == ["bad_node"]
    assert get_task_running_nodes(TASK_ID) == []


def test_trace_node_falls_back_to_dash_task_id():
    @node_utils.trace_node()
    def lonely_node(state):
        return state

    lonely_node({})

    assert get_task_done_nodes("-") == ["lonely_node"]
    assert get_task_running_nodes("-") == []


def test_trace_node_task_trace_can_be_disabled(monkeypatch):
    spy = _LoggerSpy()
    monkeypatch.setattr(node_utils, "logger", spy)

    @node_utils.trace_node(desc="只记日志", task_trace=False)
    def only_log(state):
        return state

    only_log({"task_id": TASK_ID})

    assert len(spy.binds) == 1  # 日志照旧
    assert len(spy.infos) == 2
    assert get_task_running_nodes(TASK_ID) == []  # 但不进任务追踪
    assert get_task_done_nodes(TASK_ID) == []


def test_trace_node_log_trace_can_be_disabled(monkeypatch):
    spy = _LoggerSpy()
    monkeypatch.setattr(node_utils, "logger", spy)

    @node_utils.trace_node(desc="只追踪任务", log_trace=False)
    def only_task(state):
        return state

    only_task({"task_id": TASK_ID})

    assert spy.binds == []  # 未绑定日志身份
    assert spy.infos == []
    assert get_task_done_nodes(TASK_ID) == ["only_task"]
    assert get_task_running_nodes(TASK_ID) == []
