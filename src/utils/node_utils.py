"""节点/步骤装饰器: `trace_node` / `node_log` / `step_log`。

- `trace_node`: 节点级统一装饰器, 同时提供「日志 + 任务追踪」。
- `node_log`  : 节点日志装饰器, 节点函数签名 `func(state, ...)`。
- `step_log`  : 步骤日志装饰器, 普通函数签名 `func(*args, **kwargs)`。

`trace_node` 内部复用 `node_log` 完成日志包装。三者统一收口在本模块,
与底层日志基础设施 (utils/logging_utils.py) 解耦。
"""

from functools import wraps
import time
from typing import Any, Callable

from utils.logging_utils import logger
from utils.task_utils import add_done_node, add_running_node


def node_log(desc: str | None = None):

    def _task_id(state) -> str:
        return state.get("task_id", "-")

    def deco(func):
        # 绑定被装饰函数的真实身份, 不再依赖栈定位
        _log = logger.bind(
            _file=func.__code__.co_filename.split("/")[-1].split("\\")[-1],
            _function=func.__name__,
            _line=func.__code__.co_firstlineno + 1,
        )

        description = desc or func.__name__

        @wraps(func)
        def wrapper(state, *args, **kwargs):    # 明确装饰函数要有一个 state 参数
            task_id = _task_id(state)
            start_ts = time.time()
            _log.info(f"节点开始 [{description}] <task_id = {task_id}>")
            try:
                result = func(state, *args, **kwargs)
                cost_ms = int((time.time() - start_ts) * 1000)
                _log.info(f"节点完成 [{description}] <task_id = {task_id}>, 耗时={cost_ms}ms")
                return result
            except Exception:
                _log.opt(exception=True).error(f"节点异常 [{description}] <task_id = {task_id}>")
                raise
        return wrapper
    return deco


def step_log(desc: str | None = None):
    def deco(func):
        # 绑定被装饰函数的真实身份, 不再依赖栈定位
        _log = logger.bind(
            _file=func.__code__.co_filename.split("/")[-1].split("\\")[-1],
            _function=func.__name__,
            _line=func.__code__.co_firstlineno + 1,
        )

        description = desc or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_ts = time.time()
            _log.info(f"步骤开始 [{description}]")
            try:
                result = func(*args, **kwargs)
                cost_ms = int((time.time() - start_ts) * 1000)
                _log.info(f"步骤完成 [{description}], 耗时={cost_ms}ms")
                return result
            except Exception:
                _log.opt(exception=True).error(f"步骤异常 [{description}]")
                raise
        return wrapper
    return deco


def _task_trace(node_name: str, *, need_push: bool = False) -> Callable[..., Any]:
    """任务追踪包装: 开始时记 running, 结束(含异常)时记 done。

    need_push 原样透传给 task_utils 的 add_running_node / add_done_node:
    是否在状态变化后立刻触发 SSE 推送。这里不做任何写死, 由装饰器使用方决定。
    """

    def deco(func):
        @wraps(func)
        def wrapper(state, *args, **kwargs):
            task_id = state.get("task_id", "-")
            add_running_node(task_id, node_name, need_push=need_push)
            try:
                return func(state, *args, **kwargs)
            finally:
                add_done_node(task_id, node_name, need_push=need_push)

        return wrapper

    return deco


def trace_node(
    desc: str | None = None,
    *,
    log_trace: bool = True,
    task_trace: bool = True,
    need_push: bool = False,
) -> Callable[..., Any]:
    """节点统一装饰器。

    参数:
        desc       节点功能描述 / 显示名, 用于日志、SSE 推送与前端展示;
                   默认取被修饰函数的函数名 `func.__name__`。
        log_trace  是否记录执行日志 (复用 `node_log`), 默认 True。
        task_trace 是否记录任务追踪; 为 True 时在节点开始时自动调用
                   `add_running_node`, 结束或异常退出时自动调用 `add_done_node`,
                   默认 True。
        need_push  任务状态变化后是否立刻触发 SSE 推送 (透传给
                   `add_running_node` / `add_done_node`), 默认 False。
                   仅在 `task_trace=True` 时有效; 需要实时进度的节点自行开启,
                   其余节点保持默认, 避免无谓推送。

    任务追踪以函数名 `func.__name__` 作为节点标识, 与 LangGraph 节点名一致。
    """

    def deco(func):
        description = desc or func.__name__

        # 内层 -> 外层: 日志 -> 任务追踪
        if log_trace:
            func = node_log(desc=description)(func)
        if task_trace:
            func = _task_trace(func.__name__, need_push=need_push)(func)

        return func

    return deco


if __name__ == "__main__":
    from typing import TypedDict

    class NodeState(TypedDict):
        task_id: int
        a: int

    # node_log: 节点日志
    @node_log("node_test")
    def node_test(state: NodeState):
        logger.info("processing...")
        state["a"] = state["a"] + 1
        return state

    start_state: NodeState = {"a": 0, "task_id": 12345}
    end_state = node_test(state=start_state)
    logger.info(end_state["a"])

    # step_log: 步骤日志
    @step_log("test step")
    def step_test(a: int, b: int):
        return a + b
    logger.info(step_test(2, 3))

    # trace_node: 日志 + 任务追踪
    from utils.task_utils import clear_task, get_task_done_nodes, get_task_running_nodes

    @trace_node(desc="演示节点")
    def demo_node(state: dict):
        return state

    clear_task("demo")
    demo_node({"task_id": "demo"})
    logger.info(f"running={get_task_running_nodes('demo')} done={get_task_done_nodes('demo')}")
