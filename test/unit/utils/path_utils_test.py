"""单元测试: src/utils/path_utils.py

被测对象:
    get_project_root    向上查找项目标记 (pyproject.toml / uv.lock / .env), 带 lru_cache
    get_src_root        src 目录, 不存在时抛 FileNotFoundError
    from_project_root   基于项目根目录拼接路径
    get_path_dir        取当前文件的上 N 级目录
    _iter_ancestors     从起始目录逐级向上产出 (含文件系统根)

注意: get_project_root / get_src_root 都带 lru_cache(maxsize=1), 用例里凡是改了
      环境变量或标记常量的, 必须清缓存, 否则会把结果泄漏给其它用例 —— 见 autouse fixture。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from utils import path_utils
from utils.path_utils import (
    from_project_root,
    get_path_dir,
    get_project_root,
    get_src_root,
)


@pytest.fixture(autouse=True)
def _clean_root_cache():
    """用例前后清空 lru_cache, 避免污染其它用例。"""
    get_project_root.cache_clear()
    get_src_root.cache_clear()
    yield
    get_project_root.cache_clear()
    get_src_root.cache_clear()


# --------------------------------------------------------------------------- #
# get_project_root: 标记查找 / 环境变量优先级 / 找不到时抛错
# --------------------------------------------------------------------------- #
def test_get_project_root_finds_marker_dir(project_root):
    root = get_project_root()

    assert root == project_root.resolve()
    # 命中 _PROJECT_MARKERS 之一
    assert (root / "pyproject.toml").is_file()


def test_get_project_root_prefers_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    assert get_project_root() == tmp_path.resolve()


def test_get_project_root_falls_back_when_env_var_is_not_a_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path / "not-exist"))

    # 环境变量指向的不是目录 -> 回退到向上查找
    assert get_project_root().name == "shop-assistant"


def test_get_project_root_raises_without_markers(monkeypatch):
    monkeypatch.delenv("PROJECT_ROOT", raising=False)
    monkeypatch.setattr(path_utils, "_PROJECT_MARKERS", ("definitely-no-such-marker",))

    with pytest.raises(FileNotFoundError):
        get_project_root()


def test_get_project_root_is_cached():
    first = get_project_root()

    assert get_project_root() is first
    assert get_project_root.cache_info().maxsize == 1


# --------------------------------------------------------------------------- #
# get_src_root
# --------------------------------------------------------------------------- #
def test_get_src_root(project_root):
    assert get_src_root() == project_root.resolve() / "src"


def test_get_src_root_raises_when_src_missing(monkeypatch, tmp_path):
    # 把项目根指向一个没有 src 的目录
    monkeypatch.setattr(path_utils, "get_project_root", lambda: tmp_path)

    with pytest.raises(FileNotFoundError):
        get_src_root()


# --------------------------------------------------------------------------- #
# from_project_root / get_path_dir
# --------------------------------------------------------------------------- #
def test_from_project_root_points_to_real_dir():
    data_dir = from_project_root("test/test-data")

    assert data_dir == get_project_root() / "test" / "test-data"
    assert data_dir.is_dir()


def test_get_path_dir_walks_up_from_this_module(project_root):
    # src/utils/path_utils.py: parents[0]=utils, parents[1]=src, parents[2]=项目根
    assert get_path_dir(0).name == "utils"
    assert get_path_dir(1) == project_root.resolve() / "src"
    assert get_path_dir(2) == project_root.resolve()


# --------------------------------------------------------------------------- #
# _iter_ancestors
# --------------------------------------------------------------------------- #
def test_iter_ancestors_covers_start_to_filesystem_root(tmp_path):
    start = tmp_path.resolve()
    chain = list(path_utils._iter_ancestors(tmp_path))

    assert chain[0] == start
    assert chain[1] == start.parent
    # 含文件系统根, 且不漏层
    assert chain[-1] == Path(start.anchor)
    assert len(chain) == len(start.parents) + 1
