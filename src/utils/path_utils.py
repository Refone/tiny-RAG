import os
from pathlib import Path
from functools import lru_cache

def get_path_dir(ps:int = 0)->Path:
    """
    pathlib.Path 提供了 parents 属性, 这是一个有序的路径上级目录迭代器, 直接通过索引取值就能快速获取「上 N 级目录」, 完美解决多层 .parent 繁琐的问题, 这也是官方推荐的简化写法！
    核心规则: parents[N] 索引对应「向上的层级数」
    parents[0] → 等价于 .parent (当前路径的上 1 级目录)
    parents[1] → 等价于 .parent.parent (当前路径的上 2 级目录)
    parents[2] → 等价于 .parent.parent.parent (当前路径的上 3 级目录)
    以此类推, parents[N] → 直接获取上 N+1 级目录, 索引越⼤, 层级越靠上
    :param ps:
    :return:
    """
    dir_path = Path(__file__).parents[ps]
    return dir_path

# 项目根目录的“地标”: 命中任意一项即认为是根目录
_PROJECT_MARKERS = ("pyproject.toml", "uv.lock", ".env")

def _iter_ancestors(start: Path):
    """从 start 开始逐级向上产出目录, 直到文件系统根目录 (含) 。"""
    current = start.resolve()
    while True:
        yield current
        parent = current.parent
        if parent == current:      # 到达根目录, 父目录等于自己
            return
        current = parent

@lru_cache(maxsize=1)
def get_project_root() -> Path:
    # 1. 环境变量优先: 生产 / 容器 / CI 显式指定
    env_root = os.getenv("PROJECT_ROOT")
    if env_root:
        candidate = Path(env_root).resolve()
        if candidate.is_dir():
            return candidate

    # 2. 从本文件位置向上查找项目标记
    start = Path(__file__).resolve().parent
    for directory in _iter_ancestors(start):
        if any((directory / m).exists() for m in _PROJECT_MARKERS):
            return directory

    raise FileNotFoundError(
        f"未找到项目根目录 (需包含 {_PROJECT_MARKERS} 之一) , "
        "且未设置环境变量 PROJECT_ROOT"
    )

@lru_cache(maxsize=1)
def get_src_root() -> Path:
    src = get_project_root() / "src"
    if not src.is_dir():
        raise FileNotFoundError(f"未找到 src 目录: {src}")
    return src

if __name__ == "__main__":
    print(get_project_root())
    print(get_src_root())
    print(get_path_dir(0))
    print(get_path_dir(1))
    print(get_path_dir(2))