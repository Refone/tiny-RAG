
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

局限 (TODO, 见 U7):
    这四个字典是**进程内**全局状态: 没有加锁、没有淘汰策略, 且多 uvicorn worker
    部署时每个进程各持一份, 任务状态查询与 SSE 推送会跨进程不一致。
    当前按「单 worker」使用; 若要多 worker 部署, 需改为 Redis 等外部存储,
    或把任务状态收敛到单一进程 (例如独立的任务服务)。
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
#   add_done_node          : 向「已完成」列表追加(去重)并从「运行中」出队, 可选推送 SSE
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
    """将节点加入该任务的「已完成」列表(去重), 并从「运行中」列表出队。

    Args:
        task_id: 任务 ID。
        node_name: 节点名称。
        need_push: 是否在本次调用后触发 SSE 推送, 默认 False。
    """
    if node_name not in _tasks_done_nodes[task_id]:
        _tasks_done_nodes[task_id].append(node_name)

    # 用 get 而不是下标: 避免给从未跑过的 task 凭空建出条目
    running = _tasks_running_nodes.get(task_id)
    if running and node_name in running:
        running.remove(node_name)

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
    """读取任务「已完成」节点列表的副本, 不存在时返回空列表(无副作用)。

    返回副本而不是内部 list: 调用方 (API / SSE 拼装) 顺手 append 时不会污染全局状态。
    """
    return list(_tasks_done_nodes.get(task_id, []))


def get_task_running_nodes(task_id: str) -> List[str]:
    """读取任务「运行中」节点列表的副本, 不存在时返回空列表(无副作用)。

    返回副本而不是内部 list, 理由同 get_task_done_nodes。
    """
    return list(_tasks_running_nodes.get(task_id, []))


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
