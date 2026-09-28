"""单元测试: src/utils/logging_utils.py

被测对象:
    _can_write_log_dir   日志目录可写性探测 (EAFP: 直接试写一个探针文件)
    init_logger          按 ENV_CONFIG.log 重新配置 loguru (控制台 / 文件两个开关)
    fix_log_position     修正日志的 file / function / line 字段

说明:
    - init_logger() 操作的是全局 loguru logger (`_logger.remove()`), 因此 autouse
      fixture 在每个用例结束后按真实 ENV_CONFIG 重新初始化, 不把测试配置泄漏给其它模块。
    - 对 `_logger` 的替换一律用 pytest.MonkeyPatch.context(), 退出 with 即自动还原,
      不必关心 fixture 的销毁顺序。
    - 这里断言的是「传给 loguru 的参数」而不是「日志有没有打出来」: init_logger 用的是
      enqueue=True 异步写盘, 直接断言输出会不稳定。
"""

from __future__ import annotations

import inspect
import sys
import threading

import pytest

from utils import logging_utils


class _LoggerSpy:
    """最小 loguru 替身: 记录 remove / add / warning 调用。"""

    def __init__(self) -> None:
        self.removed = 0
        self.added: list[dict] = []
        self.warnings: list[str] = []

    def remove(self, *args, **kwargs) -> None:
        self.removed += 1

    def add(self, **kwargs):
        self.added.append(kwargs)
        return len(self.added)

    def warning(self, message, *args, **kwargs) -> None:
        self.warnings.append(message)


class _FakeFrame:
    """inspect.stack() 元素的替身, 只带 fix_log_position 用到的三个字段。"""

    def __init__(self, filename: str, function: str, lineno: int) -> None:
        self.filename = filename
        self.function = function
        self.lineno = lineno


@pytest.fixture(autouse=True)
def _restore_logger():
    """用例结束后按真实 ENV_CONFIG 重建全局 loguru sink。"""
    yield
    logging_utils.init_logger()


# --------------------------------------------------------------------------- #
# _can_write_log_dir
# --------------------------------------------------------------------------- #
def test_can_write_log_dir_creates_dir_and_cleans_probe(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(logging_utils, "LOG_DIR", log_dir)

    assert logging_utils._can_write_log_dir() is True
    assert log_dir.is_dir()
    # 探针文件必须被删掉, 不留垃圾
    assert list(log_dir.iterdir()) == []


def test_can_write_log_dir_false_when_path_blocked(monkeypatch, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file")
    # 父路径是文件 -> mkdir 必然抛 OSError
    monkeypatch.setattr(logging_utils, "LOG_DIR", blocker / "logs")

    assert logging_utils._can_write_log_dir() is False


def test_can_write_log_dir_is_thread_safe(monkeypatch, tmp_path):
    """回归 U8: 并发探测时各线程的探针文件必须互不干扰。

    探针名只带 pid 时, 同进程多线程会互相 unlink 对方的探针, 把可写误判为不可写。
    """
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(logging_utils, "LOG_DIR", log_dir)

    thread_count = 8
    results: list[bool] = []
    barrier = threading.Barrier(thread_count)

    def probe() -> None:
        barrier.wait()  # 尽量让所有线程同时进入临界区
        results.append(logging_utils._can_write_log_dir())

    threads = [threading.Thread(target=probe) for _ in range(thread_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == [True] * thread_count
    assert list(log_dir.iterdir()) == []  # 探针全部清理干净


# --------------------------------------------------------------------------- #
# init_logger: 控制台开关
# --------------------------------------------------------------------------- #
def test_init_logger_adds_console_sink_only():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(logging_utils.ENV_CONFIG.log, "console_enable", True)
        mp.setattr(logging_utils.ENV_CONFIG.log, "file_enable", False)
        spy = _LoggerSpy()
        mp.setattr(logging_utils, "_logger", spy)

        result = logging_utils.init_logger()

        assert result is spy
        assert spy.removed == 1  # 先清空旧 sink
        assert len(spy.added) == 1
        console = spy.added[0]
        assert console["sink"] is sys.stdout
        assert console["level"] == logging_utils.ENV_CONFIG.log.console_level
        assert console["format"] == logging_utils.LOG_FORMAT
        assert console["colorize"] is True
        assert console["enqueue"] is True
        assert spy.warnings == []


def test_init_logger_adds_nothing_when_both_disabled():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(logging_utils.ENV_CONFIG.log, "console_enable", False)
        mp.setattr(logging_utils.ENV_CONFIG.log, "file_enable", False)
        spy = _LoggerSpy()
        mp.setattr(logging_utils, "_logger", spy)

        logging_utils.init_logger()

        assert spy.removed == 1
        assert spy.added == []
        assert spy.warnings == []


# --------------------------------------------------------------------------- #
# init_logger: 文件开关
# --------------------------------------------------------------------------- #
def test_init_logger_adds_file_sink_with_config(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    log_path = log_dir / "app_test.log"
    monkeypatch.setattr(logging_utils, "LOG_DIR", log_dir)
    monkeypatch.setattr(logging_utils, "LOG_FILE_PATH", log_path)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(logging_utils.ENV_CONFIG.log, "console_enable", False)
        mp.setattr(logging_utils.ENV_CONFIG.log, "file_enable", True)
        spy = _LoggerSpy()
        mp.setattr(logging_utils, "_logger", spy)

        logging_utils.init_logger()

        assert len(spy.added) == 1
        file_sink = spy.added[0]
        assert file_sink["sink"] == log_path
        assert file_sink["level"] == logging_utils.ENV_CONFIG.log.file_level
        assert file_sink["rotation"] == "00:00"
        assert file_sink["retention"] == logging_utils.ENV_CONFIG.log.file_retention
        assert file_sink["encoding"] == "utf-8"
        assert file_sink["delay"] is True  # 第一条日志才建文件
        assert spy.warnings == []


def test_init_logger_adds_console_then_file(monkeypatch, tmp_path):
    log_path = tmp_path / "logs" / "app_test.log"
    monkeypatch.setattr(logging_utils, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(logging_utils, "LOG_FILE_PATH", log_path)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(logging_utils.ENV_CONFIG.log, "console_enable", True)
        mp.setattr(logging_utils.ENV_CONFIG.log, "file_enable", True)
        spy = _LoggerSpy()
        mp.setattr(logging_utils, "_logger", spy)

        logging_utils.init_logger()

        assert [item["sink"] for item in spy.added] == [sys.stdout, log_path]


def test_init_logger_skips_file_sink_when_dir_unwritable(
    monkeypatch, tmp_path, capsys
):
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file")
    monkeypatch.setattr(logging_utils, "LOG_DIR", blocker / "logs")
    monkeypatch.setattr(logging_utils, "LOG_FILE_PATH", blocker / "logs" / "app.log")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(logging_utils.ENV_CONFIG.log, "console_enable", False)
        mp.setattr(logging_utils.ENV_CONFIG.log, "file_enable", True)
        spy = _LoggerSpy()
        mp.setattr(logging_utils, "_logger", spy)

        logging_utils.init_logger()

        assert spy.added == []  # 目录不可写 -> 不添加文件 sink
        assert spy.warnings == []  # 不再走 loguru: 此刻它可能 0 个 sink, 写了也没人看

    # 降级告警必须落到 stderr, 否则 console_enable=False 时完全静默
    stderr = capsys.readouterr().err
    assert "日志目录不可写" in stderr
    assert str(blocker / "logs") in stderr


# --------------------------------------------------------------------------- #
# fix_log_position
# --------------------------------------------------------------------------- #
def test_position_prefers_bound_extra(monkeypatch):
    record = {
        "extra": {"_file": "node_entry.py", "_function": "node_entry", "_line": 42}
    }

    def _explode():
        raise AssertionError("命中 extra 时不应回退到 inspect.stack()")

    monkeypatch.setattr(logging_utils.inspect, "stack", _explode)

    logging_utils.fix_log_position(record)

    # 显式绑定的位置信息优先, 且完全覆盖原值
    assert (record["file"], record["function"], record["line"]) == (
        "node_entry.py",
        "node_entry",
        42,
    )


def test_position_falls_back_to_caller_frame():
    """没有绑定 extra 时, 跳过日志基础设施的 frame, 取真正的调用方 (走真实调用栈)。"""
    record = {"extra": {}}

    expected_line = inspect.currentframe().f_lineno + 1
    logging_utils.fix_log_position(record)

    assert record["file"] == "logging_utils_test.py"
    assert record["function"] == "test_position_falls_back_to_caller_frame"
    assert record["line"] == expected_line


def test_position_skips_library_and_own_frames(monkeypatch):
    """用假 stack 覆盖 _this_is_logging_frame: loguru 内部与本模块的 frame 都要跳过。

    真实调用栈里凑不齐 loguru 内部 frame, 所以这里直接喂假 frame。
    """
    record = {"extra": {}}
    frames = [
        _FakeFrame("/x/site-packages/loguru/_logger.py", "log", 10),  # loguru 内部
        _FakeFrame("/x/site-packages/loguru/_handler.py", "emit", 15),  # loguru 内部
        _FakeFrame("/x/src/utils/logging_utils.py", "fix_log_position", 20),  # 本模块
        _FakeFrame("/x/test/unit/utils/some_test.py", "real_caller", 33),  # 真正的调用方
    ]
    monkeypatch.setattr(logging_utils.inspect, "stack", lambda: frames)

    logging_utils.fix_log_position(record)

    assert (record["file"], record["function"], record["line"]) == (
        "some_test.py",
        "real_caller",
        33,
    )


def test_position_keeps_user_frames_named_like_logging(monkeypatch):
    """回归 U1: 函数名里含 "_log" 的正常业务函数不应被跳过。

    早先的实现用 `'_log' in frame.function` 过滤, 会把 sync_log_files 这类调用方
    的 frame 跳过, 日志归属错位到它的上一层调用方。
    """
    record = {"extra": {}}
    frames = [
        _FakeFrame("/x/src/utils/logging_utils.py", "fix_log_position", 20),  # 本模块 -> 跳过
        _FakeFrame("/x/src/sync_log_files.py", "sync_log_files", 25),  # 用户函数 -> 必须选中
        _FakeFrame("/x/src/orchestrator.py", "orchestrator", 40),
    ]
    monkeypatch.setattr(logging_utils.inspect, "stack", lambda: frames)

    logging_utils.fix_log_position(record)

    assert (record["file"], record["function"], record["line"]) == (
        "sync_log_files.py",
        "sync_log_files",
        25,
    )


# --------------------------------------------------------------------------- #
# 模块导出
# --------------------------------------------------------------------------- #
def test_module_exports_patched_logger():
    # logger 是 base_logger.patch(fix_log_position) 的产物, 不是原始 logger
    assert logging_utils.logger is not logging_utils._logger
    assert callable(logging_utils.logger.info)
