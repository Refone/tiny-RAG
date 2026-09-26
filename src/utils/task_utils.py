
from collections import defaultdict
from enum import StrEnum
from typing import Dict, List

"""
任务管理器: 维护四个任务字典

    dict name            |   key     |   value
----------------------------------------------------------
_tasks_running_nodes     | task_id   | 节点列表  (["node_entry", "node_md_img", ...])
_tasks_done_nodes        | task_id   | 节点列表  (["node_entry", "node_md_img", ...])
_tasks_status            | task_id   | 状态字符串 ("pending" | "processing" ...)
_tasks_result            | task_id   | 任务结果   ({ "result": "ok" })

使用 defaultdict, 防止 id 第一次 _tasks_running_nodes['<id>'].append('...') 时,
列表未初始化导致 append 直接崩溃
"""
_tasks_running_nodes: Dict[str, List[str]] = defaultdict(list)
_tasks_done_nodes: Dict[str, List[str]] = defaultdict(list)
_tasks_status: Dict[str, str] = {}
_tasks_result: Dict[str, Dict[str, str]] = defaultdict(dict)


class TaskStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


# 合法任务状态集合, 供 set_task_status 做校验
_TASK_STATUS_VALUES = frozenset(status.value for status in TaskStatus)


# API 一览 (一个 API 一行):
#   add_running_node       : 向「运行中」节点列表追加节点(去重), 可选推送 SSE
#   add_done_node          : 向「已完成」节点列表追加节点(去重), 可选推送 SSE
#   set_task_result        : 写入任务的某个结果字段
#   get_task_result        : 读取任务的某个结果字段, 不存在时返回默认值
#   set_task_status        : 设置任务状态(必须是 TaskStatus 合法值)
#   get_task_status        : 读取任务状态, 未设置时返回空字符串
#   get_task_done_nodes    : 读取任务「已完成」节点列表
#   get_task_running_nodes : 读取任务「运行中」节点列表
#   task_push_sse          : 推送任务快照给 SSE 模块(待对接)
#   clear_task             : 清空指定任务的全部数据(幂等)


def add_running_node(task_id: str, node_name: str, need_push: bool = False) -> None:
    """将节点加入该任务的「运行中」列表(去重), 可选触发 SSE 推送。

    Args:
        task_id: 任务 ID。
        node_name: 节点名称。
        need_push: 是否在本次调用后触发 SSE 推送, 默认 False。
    """
    if node_name not in _tasks_running_nodes[task_id]:
        _tasks_running_nodes[task_id].append(node_name)

    if need_push:
        task_push_sse(task_id)


def add_done_node(task_id: str, node_name: str, need_push: bool = False) -> None:
    """将节点加入该任务的「已完成」列表(去重), 可选触发 SSE 推送。

    Args:
        task_id: 任务 ID。
        node_name: 节点名称。
        need_push: 是否在本次调用后触发 SSE 推送, 默认 False。
    """
    if node_name not in _tasks_done_nodes[task_id]:
        _tasks_done_nodes[task_id].append(node_name)

    if need_push:
        task_push_sse(task_id)


def set_task_result(task_id: str, key: str, value: str) -> None:
    """写入任务的某个结果字段, 同名 key 会被覆盖。"""
    _tasks_result[task_id][key] = value


def get_task_result(task_id: str, key: str, default: str = "") -> str:
    """读取任务的某个结果字段, 不存在时返回 default(默认空字符串, 无副作用)。"""
    return _tasks_result.get(task_id, {}).get(key, default)


def get_task_status(task_id: str) -> str:
    """读取任务状态, 任务不存在或未设置时返回空字符串。"""
    return _tasks_status.get(task_id, "")


def set_task_status(task_id: str, status: str) -> None:
    """设置任务状态, status 必须是 TaskStatus 中的合法值, 否则抛 ValueError。"""
    if status not in _TASK_STATUS_VALUES:
        raise ValueError(
            f"非法任务状态: {status!r}, 合法值: {sorted(_TASK_STATUS_VALUES)}"
        )
    _tasks_status[task_id] = status


def get_task_done_nodes(task_id: str) -> List[str]:
    """读取任务「已完成」节点列表, 不存在时返回空列表(无副作用)。"""
    return _tasks_done_nodes.get(task_id, [])


def get_task_running_nodes(task_id: str) -> List[str]:
    """读取任务「运行中」节点列表, 不存在时返回空列表(无副作用)。"""
    return _tasks_running_nodes.get(task_id, [])


def task_push_sse(task_id: str) -> None:
    """将任务快照推送给 SSE 模块。

    TODO: 未来对接 sse 模块, 目前为空实现(pass)。
    """
    pass


def clear_task(task_id: str) -> None:
    """清空指定任务的全部数据(运行/完成/状态/结果), 幂等, 不存在时不报错。"""
    _tasks_running_nodes.pop(task_id, None)
    _tasks_done_nodes.pop(task_id, None)
    _tasks_status.pop(task_id, None)
    _tasks_result.pop(task_id, None)


if __name__ == "__main__":
    # 定义颜色常量
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    RESET = "\033[0m"

    def _case(name: str, fn) -> None:
        try:
            fn()
            print(f"[{GREEN}PASS{RESET}] {name}")
        except AssertionError as exc:
            print(f"[{RED}FAIL{RESET}] {name}: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"[{YELLOW}ERROR{RESET}] {name}: {exc!r}")

    # --- TaskStatus 枚举 ---
    def test_task_status_values():
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.COMPLETE == "complete"
        assert "failed" in TaskStatus
        assert "bogus" not in TaskStatus

    # --- 运行中节点: 追加与去重 ---
    def test_add_running_node_dedup():
        clear_task("t1")
        add_running_node("t1", "node_a")
        add_running_node("t1", "node_a")  # 重复, 应被去重
        add_running_node("t1", "node_b")
        assert get_task_running_nodes("t1") == ["node_a", "node_b"]

    # --- 完成节点: 追加与去重 ---
    def test_add_done_node_dedup():
        clear_task("t1")
        add_done_node("t1", "node_a")
        add_done_node("t1", "node_a")  # 重复, 应被去重
        add_done_node("t1", "node_b")
        assert get_task_done_nodes("t1") == ["node_a", "node_b"]

    # --- 结果读写与默认值 ---
    def test_result_get_set():
        clear_task("t1")
        assert get_task_result("t1", "k") == ""
        assert get_task_result("t1", "k", "dft") == "dft"
        set_task_result("t1", "k", "v1")
        set_task_result("t1", "k", "v2")  # 覆盖旧值
        assert get_task_result("t1", "k") == "v2"

    # --- 状态读写与默认值 ---
    def test_status_get_set():
        clear_task("t1")
        assert get_task_status("t1") == ""  # 未设置时不抛 KeyError
        set_task_status("t1", TaskStatus.PROCESSING)
        assert get_task_status("t1") == "processing"

    # --- 非法状态应抛 ValueError ---
    def test_status_invalid_raises():
        clear_task("t1")
        try:
            set_task_status("t1", "not-a-status")
        except ValueError:
            return
        assert False, "非法的状态应抛出 ValueError"

    # --- 读取不存在的任务: 返回空且无副作用 ---
    def test_get_missing_task_no_side_effect():
        clear_task("no-such-task")
        assert get_task_running_nodes("no-such-task") == []
        assert get_task_done_nodes("no-such-task") == []
        assert get_task_status("no-such-task") == ""
        assert get_task_result("no-such-task", "k") == ""
        # 读操作不应在字典里留下条目
        assert "no-such-task" not in _tasks_running_nodes
        assert "no-such-task" not in _tasks_done_nodes
        assert "no-such-task" not in _tasks_status
        assert "no-such-task" not in _tasks_result

    # --- need_push 触发 SSE 推送 ---
    def test_need_push_triggers_sse():
        global task_push_sse
        clear_task("t1")
        pushed = []
        original = task_push_sse
        task_push_sse = lambda tid: pushed.append(tid)
        try:
            add_running_node("t1", "node_a", need_push=True)
            add_done_node("t1", "node_a", need_push=True)
            add_running_node("t1", "node_b", need_push=False)  # 不推送
        finally:
            task_push_sse = original
        assert pushed == ["t1", "t1"]

    # --- clear_task 幂等 ---
    def test_clear_task_idempotent():
        clear_task("t1")
        add_running_node("t1", "node_a")
        set_task_status("t1", TaskStatus.PENDING)
        set_task_result("t1", "k", "v")
        clear_task("t1")
        assert get_task_running_nodes("t1") == []
        assert get_task_status("t1") == ""
        assert get_task_result("t1", "k") == ""
        clear_task("t1")  # 再次清空不报错
        clear_task("never-exists")  # 清空不存在的任务不报错

    # --- defaultdict: 首次直接 append 不崩 ---
    def test_defaultdict_first_append():
        clear_task("t2")
        _tasks_running_nodes["t2"].append("node_x")
        assert get_task_running_nodes("t2") == ["node_x"]

    cases = [
        ("TaskStatus 枚举值", test_task_status_values),
        ("运行中节点去重", test_add_running_node_dedup),
        ("完成节点去重", test_add_done_node_dedup),
        ("结果读写与默认值", test_result_get_set),
        ("状态读写与默认值", test_status_get_set),
        ("非法状态抛 ValueError", test_status_invalid_raises),
        ("读取不存在任务无副作用", test_get_missing_task_no_side_effect),
        ("need_push 触发 SSE", test_need_push_triggers_sse),
        ("clear_task 幂等", test_clear_task_idempotent),
        ("defaultdict 首次 append", test_defaultdict_first_append),
    ]

    for name, fn in cases:
        _case(name, fn)
