from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from utils.path_util import get_project_root

"""
    该文件从 .env 文件中读取配置信息
    读取规则:
    TODO
"""
BASE_DIR = get_project_root()
ENV_FILE = BASE_DIR / ".env"

BASE_CONFIG = {
    "env_file": ENV_FILE,
    "env_file_encoding": "utf-8",
    "extra": "ignore"
}

class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class LogSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **BASE_CONFIG,
        env_prefix="LOG_"
    )

    console_enable: bool = False
    console_level: LogLevel = LogLevel.INFO
    file_enable: bool = False
    file_level: LogLevel = LogLevel.DEBUG
    file_retention: str = "7 days"
    file_dir: str = str(get_project_root() / "logs")

class Settings(BaseSettings):
    log: LogSettings = Field(default_factory=LogSettings)

@lru_cache
def get_global_settings() -> Settings:
    return Settings()

config = get_global_settings()

if __name__ == "__main__":
    from rich import print as rprint
    rprint(config)