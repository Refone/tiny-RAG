import inspect
import os
from pathlib import Path
import sys
import uuid

from loguru import logger as _logger
from common.config.settings import config

LOG_FORMAT = (
    "<yellow>{time:YYYY-MM-DD HH:mm:ss.SSS}</yellow> | "
    "<level>{level:<7}</level> | "
    "<cyan>{file}</cyan>:<cyan>{line}</cyan> <cyan>{function}</cyan> | "
    "<level>{message}</level>"
)
LOG_DIR = Path(config.log.file_dir)
LOG_FILE_NAME = "app_{time:YYYYMMDD}.log"
LOG_FILE_PATH = LOG_DIR / LOG_FILE_NAME

def _can_write_log_dir() -> bool:
    """实际在日志目录写入一个临时文件, 判断是否可写。

    不用 os.access: 它在「权限位」与「真实 open」不一致时 (只读挂载/容器/沙箱)
    会误判; 且日志目录首次运行时可能不存在。这里用 EAFP, 直接试一次写。
    """
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        # 探针名带 uuid: 只用 pid 的话, 同进程多线程并发探测时会互相删掉对方的探针
        # (touch -> unlink 竞态), 把「可写」误判成「不可写」, 静默关掉文件日志。
        probe = LOG_DIR / f".write_probe_{os.getpid()}_{uuid.uuid4().hex}"
        probe.touch()
        probe.unlink()
        return True
    except OSError:
        return False


def init_logger():
    # 1. 删除所有默认 logger, 重新进行配置
    _logger.remove()

    if config.log.console_enable:
        _logger.add(
            sink=sys.stdout,
            level=config.log.console_level,
            format=LOG_FORMAT,
            colorize=True,
            backtrace=False,
            enqueue=True,   # 异步写日志, 可能被同步 print “后来居上”
        )

    if config.log.file_enable:
        if _can_write_log_dir():
            _logger.add(
                sink=LOG_FILE_PATH,
                level=config.log.file_level,
                format=LOG_FORMAT,
                rotation="00:00",
                retention=config.log.file_retention,
                encoding="utf-8",
                enqueue=True,
                backtrace=True,
                diagnose=True,
                delay=True,          # 第一条日志才建文件
            )
        else:
            # 注意: 上面已经 _logger.remove() 清空全部 sink, 若 console_enable=False
            # 则此刻一个 sink 都没有, _logger.warning 会被直接丢弃 (降级完全静默)。
            # 因此这里直接写 stderr 兜底, 保证运维一定看得到。
            print(f"日志目录不可写, 已跳过文件日志: {LOG_DIR}", file=sys.stderr)

    return _logger

base_logger = init_logger()

def fix_log_position(record):
    """
    为了在其他文件中调用 logger 打印
    能正常追踪文件与函数名
    这里需要剔除 logging 模块的 frame
    """
    # 优先使用显式绑定的位置信息 (node_log / step_log 会绑定真实身份)
    extra = record.get("extra", {})
    if "_file" in extra:
        record.update(
            file=extra["_file"],
            function=extra["_function"],
            line=extra["_line"],
        )
        return

    def _this_is_logging_frame(frame):
        """判断 frame 是否属于日志基础设施自身 (本模块 / loguru 内部)。

        只按文件路径判断。早先用 `'_log' in frame.function` 过滤, 会把函数名里含
        "_log" 的正常业务函数 (如 sync_log_files) 一并跳过, 日志归属错位到它的
        上一层调用方, file/line 也跟着错 —— 见 test/unit/utils/logging_utils_test.py
        的 test_position_keeps_user_frames_named_like_logging。
        """
        filename = frame.filename.replace("\\", "/")
        if filename.rsplit("/", 1)[-1] == "logging_utils.py":
            return True
        return "/loguru/" in filename

    for frame in inspect.stack():
        if _this_is_logging_frame(frame):
            continue
        record.update(
            file=frame.filename.split("/")[-1].split("\\")[-1],
            function=frame.function,
            line=frame.lineno
        )
        break


logger = base_logger.patch(fix_log_position)

if __name__ == '__main__':
    logger.debug("这是一条 DEBUG 信息")
    logger.info("这是一条 INFO 信息")
    logger.warning("这是一条 WARN 信息")
    logger.error("这是一条 ERROR 信息")
