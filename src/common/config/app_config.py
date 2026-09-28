from dataclasses import dataclass
from typing import Final, List

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

APP_CONFIG: Final[_AppConfig] = _AppConfig()