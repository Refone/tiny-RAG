"""节点注册器: 全局节点映射表 + 注册装饰器 + 访问器。

这里只负责「注册」这一件事, 与日志解耦:
    - 注册用 `@register` (本模块);
    - 日志用 `@node_log` (utils/logging_utils.py)。

两者在节点文件里堆叠使用, 注册装饰器放在最外层:

    @register(cn="检查文件", description="...")   # 外层: 把函数登记进 NODES
    @node_log()                                   # 内层: 包装日志
    def node_entry(state): ...

这样 `NODES` 里存的是「已包日志的函数」, 图执行时才有日志输出。
规范名统一取函数名 `func.__name__`, 与 LangGraph 节点名一致。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterator

if TYPE_CHECKING:  # 仅类型检查时引用, 运行时零导入, 避免循环依赖
    from processor.import_processor.state import ImportNodeState

# 节点函数签名: 接收 state 并返回 state
NodeFunc = Callable[["ImportNodeState"], "ImportNodeState"]


@dataclass(frozen=True)
class NodeMeta:
    """一个节点的自描述元信息 (映射表 `NODES` 的 value)。"""

    cn: str                 # 中文显示名 (进度/前端/展示层)
    func: NodeFunc          # 节点实现 (已带日志包装)
    description: str = ""   # 一句话说明, 起代码自解释作用

    def __call__(self, state: "ImportNodeState") -> "ImportNodeState":
        """让 NodeMeta 可以像节点函数一样被直接调用。"""
        return self.func(state)

    def __str__(self) -> str:
        return self.cn


# 全局映射表: 规范名(函数名) -> NodeMeta, 插入有序
NODES: dict[str, NodeMeta] = {}


def register(cn: str, *, description: str = "") -> Callable[[NodeFunc], NodeFunc]:
    """节点注册装饰器 (pass-through)。

    把函数按规范名 (函数名) 登记进 `NODES`, 原样返回函数, 不影响堆叠。
    """

    def deco(func: NodeFunc) -> NodeFunc:
        NODES[func.__name__] = NodeMeta(cn=cn, func=func, description=description)
        return func

    return deco


# ============================================================
# 访问器: 统一的只读入口
# ============================================================
def get_node(name: str) -> NodeMeta:
    """按规范名 (函数名) 取节点元信息。"""
    try:
        return NODES[name]
    except KeyError:
        valid = ", ".join(sorted(NODES))
        raise KeyError(f"未知节点 {name!r}, 合法节点: {valid}") from None


def get_cn(name: str) -> str:
    """取中文显示名。"""
    return get_node(name).cn


def get_func(name: str) -> NodeFunc:
    """取节点实现函数 (已带日志包装)。"""
    return get_node(name).func


def iter_nodes() -> Iterator[tuple[str, NodeMeta]]:
    """按注册顺序遍历 (规范名, 元信息)。"""
    return iter(NODES.items())


def node_names() -> list[str]:
    """所有规范名 (字符串)。"""
    return list(NODES)
