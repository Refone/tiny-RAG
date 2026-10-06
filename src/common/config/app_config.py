from dataclasses import dataclass
import os
from typing import Final

@dataclass(frozen=True)
class _AppConfig:
    # 支持的图片格式
    support_image_format: tuple[str, ...] = (
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "webp"
    )

    # 解释 Markdown 中图片时, 最大探测前后的字符数
    md_image_surrounding_context_max_chars: int = 500

    # 调用 VLM 获取图像摘要时的最大并发数
    vlm_max_concurrent_requests: int = os.cpu_count() - 1
    # VLM 请求超时时间 (秒)
    vlm_request_timeout: int = 30
    # VLM 请求重试次数
    vlm_request_retry_attempts: int = 3

    # 切分 Markdown 内容时的配置（软限制）
    max_chunk_size: int = 1000
    min_chunk_size: int = 200
    overlap_size: int = 100


APP_CONFIG: Final[_AppConfig] = _AppConfig()