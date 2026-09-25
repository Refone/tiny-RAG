from enum import StrEnum
from pathlib import Path


class DocType(StrEnum):
    UNKNOWN = "<unk>"
    PDF = "pdf"
    MARKDOWN = "md"

    @classmethod
    def from_filename(cls, filename: str) -> "DocType":
        """
        根据文件名后缀判断文档类型, 无法识别时返回 UNKNOWN。
        """
        ext = Path(filename).suffix.lower().lstrip(".")
        return _EXT_TO_DOC_TYPE.get(ext, DocType.UNKNOWN)


# 文件后缀 -> DocType 映射
_EXT_TO_DOC_TYPE = {
    "pdf": DocType.PDF,
    "md": DocType.MARKDOWN,
    "markdown": DocType.MARKDOWN,
}


if __name__ == "__main__":
    from rich import print as rprint

    for name in ("a.pdf", "b.MD", "c.markdown", "d.unknown"):
        rprint(f"{name!r:>14} -> {DocType.from_filename(name)!r}")
