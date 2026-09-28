"""单元测试: src/common/config/env_config.py

被测对象:
    LogSettings / MineruSettings   配置模型 (env_prefix: LOG_ / MINERU_)
    Settings                       聚合配置
    get_global_settings            带 lru_cache 的全局配置入口 (导出为 ENV_CONFIG)

TODO: 补充用例
    - 默认值: log.console_enable=False, mineru.base_url="https://mineru.net/api/v4"
    - monkeypatch.setenv 后 LOG_CONSOLE_ENABLE / MINERU_API_KEY 能覆盖默认值
    - 未声明的多余环境变量被忽略 (extra="ignore")
    - 非法 log level 抛 pydantic 的 ValidationError
    - get_global_settings 返回同一实例 (lru_cache), 需要时 cache_clear()

提示: 用 monkeypatch 控制环境变量, 避免依赖本机 .env 的真实内容。
"""
