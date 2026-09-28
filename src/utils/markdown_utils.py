import re
from typing import Optional
from common.config.app_config import APP_CONFIG

# 一个或多个空行（允许行内只有空格/制表符）
_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n")
_IMG_MD_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MEANINGLESS_CHARS_RE = re.compile(r"[\s\[\]()（）【】]+")

def _is_image_only(segment: str) -> bool:
    """段落去掉图片标记后若没有其它字符，则视为纯图片段落。"""
    stripped = _IMG_MD_RE.sub("", segment)
    stripped = _MEANINGLESS_CHARS_RE.sub("", stripped)
    return stripped == ""


def _clean_segment(segment: str) -> str:
    """去掉段落中的图片标记，并清理多余空白。"""
    return _IMG_MD_RE.sub("", segment).strip()


def extract_surrounding_context(
    md_content: str,
    start: int,
    end: int,
    max_chars: int = APP_CONFIG.md_image_surrounding_context_max_chars,
) -> tuple[str, str]:
    """
    提取图片标记 ![alt](url) 的前一段和后一段文本。

    规则：
    - 纯图片段落会被跳过，继续往前/往后找。
    - 混合段落（文本 + 图片）保留文本，去掉图片标记。
    - 截断时，前一段保留尾部，后一段保留头部。

    Returns:
        (prev_text, next_text)：前一段、后一段，可能为空字符串
    """
    before = md_content[:start].rstrip()
    after = md_content[end:].lstrip()

    # 前一段：从后往前找第一个有文本的段落
    prev_text = ""
    for part in reversed(_BLANK_LINE_RE.split(before)):
        part = part.strip()
        if not part or _is_image_only(part):
            continue
        cleaned = _clean_segment(part)
        if not cleaned:
            continue
        prev_text = cleaned[-max_chars:]
        break

    # 后一段：从前往后找第一个有文本的段落
    next_text = ""
    for part in _BLANK_LINE_RE.split(after):
        part = part.strip()
        if not part or _is_image_only(part):
            continue
        cleaned = _clean_segment(part)
        if not cleaned:
            continue
        next_text = cleaned[:max_chars]
        break

    return prev_text, next_text

def find_image_position(md_content: str, image_name: str) -> tuple[int, int] | None:
    """
    在 Markdown 中找到图片描述符 ![...](...) 的起止位置

    Args:
        md_content: Markdown 文本
        image_name: 图片文件名
    Returns:
        (start, end): 图片描述符的起止位置, 如果没找到, 返回 None
    """
    rep = re.compile(r"\!\[.*?\]\(.*?"+re.escape(image_name)+r".*\)")
    search_match = rep.search(md_content)
    if not search_match:
        return None
    return search_match.start(), search_match.end()
