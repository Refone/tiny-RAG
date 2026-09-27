"""单元测试: src/utils/logging_utils.py

被测对象:
    init_logger          初始化 loguru 日志 (控制台 / 文件开关与级别)
    _can_write_log_dir   日志目录可写性探测
    fix_log_position     修正日志中的 file / function / line 字段

TODO: 补充用例
    - 日志目录不可写时不抛异常, 且自动关闭文件输出
    - config.log.console_enable 与 file_enable 开关分别生效
    - monkeypatch 日志目录到 tmp_path 后, 能生成 app_YYYYMMDD.log
    - 文件保留策略 (file_retention) 传入 logger.add 的参数正确

提示: 涉及真实文件系统写入的用例请用 tmp_path, 不要污染项目 logs/ 目录。
"""
