"""FastAPI 依赖注入: 集中装配配置、会话、service 实例。

当前仅演示配置读取; 后续会话管理、图实例等也在此统一提供,
避免 router 直接触碰 common/config 与 processor 内部。
"""

from common.config.env_config import ENV_CONFIG, EnvConfig


def get_env_config() -> EnvConfig:
    """注入全局配置单例。"""
    return ENV_CONFIG
