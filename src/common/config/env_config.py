from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from utils.path_utils import PROJECT_ROOT

"""
    该文件从 .env 文件中读取配置信息
    读取规则:
    TODO
"""
BASE_DIR = PROJECT_ROOT
ENV_FILE = BASE_DIR / ".env"

BASE_CONFIG = {"env_file": ENV_FILE, "env_file_encoding": "utf-8", "extra": "ignore"}


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class QwenSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_CONFIG, env_prefix="QWEN_")

    base_url: str = "https://maas.qianwenaiapi.com/compatible-mode/v1"
    api_key: str = ""


class LogSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_CONFIG, env_prefix="LOG_")

    console_enable: bool = False
    console_level: LogLevel = LogLevel.INFO
    file_enable: bool = False
    file_level: LogLevel = LogLevel.DEBUG
    file_retention: str = "7 days"
    file_dir: str = str(PROJECT_ROOT / "logs")


class MineruSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_CONFIG, env_prefix="MINERU_")

    base_url: str = "https://mineru.net/api/v4"
    api_key: str = ""
    est_per_page: float = 0.5
    timeout_per_page: float = 10
    poll_interval: float = 3
    unzip_dir: str = str(PROJECT_ROOT / "output/markdown-folder")


class VLMSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_CONFIG, env_prefix="VLM_")

    base_url: str = "https://api.siliconflow.cn/v1"
    api_key: str = ""
    model_name: str = "Qwen/Qwen3-VL-32B-Instruct"
    rpm: int = 1000


class MinioSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_CONFIG, env_prefix="MINIO_")

    endpoint: str = "127.0.0.1:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket_name: str = "knowlege-hub-files"
    image_dir: str = "upload-images"
    secure: bool = False


class EmbeddingSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_CONFIG, env_prefix="EMBEDDING_")

    model: str = "text-embedding-v4"
    rpm: int = 1000
    dense_dimension: int = 1024


class MilvusSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_CONFIG, env_prefix="MILVUS_")

    endpoint: str = "127.0.0.1:19530"
    collection_item_name: str = "kb_item_name"


class LargeLanguageModelSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_CONFIG, env_prefix="LLM_")

    base_url: str = "https://api.siliconflow.cn/v1"
    api_key: str = ""
    model_name: str = "deepseek-ai/DeepSeek-V4-Flash"
    rpm: int = 500


class EnvConfig(BaseSettings):
    log: LogSettings = Field(default_factory=LogSettings)
    mineru: MineruSettings = Field(default_factory=MineruSettings)
    vlm: VLMSettings = Field(default_factory=VLMSettings)
    minio: MinioSettings = Field(default_factory=MinioSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)
    qwen: QwenSettings = Field(default_factory=QwenSettings)
    llm: LargeLanguageModelSettings = Field(default_factory=LargeLanguageModelSettings)


ENV_CONFIG = EnvConfig()

if __name__ == "__main__":
    from rich import print as rprint

    rprint(ENV_CONFIG)
