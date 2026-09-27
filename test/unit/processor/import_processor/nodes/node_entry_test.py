"""单元测试: src/processor/import_processor/nodes/node_entry.py

被测对象:
    node_entry    入口节点: 文件存在性校验 + 类型识别 + 状态补全

说明:
    - node_entry 被 @trace_node 包装, 调用时写入 task_utils 的全局字典,
      隔离由 test/unit/conftest.py 的 clean_task_store 统一负责。
    - 正向用例复用 test/test-data 下的样例 (sample_md / sample_pdf / sample_txt)。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.enum.doc_type import DocType
from processor.import_processor.nodes.node_entry import node_entry
from processor.import_processor.state import ImportNodeState, create_state

TASK_ID = "node-entry-unit-test"


def _run(path: str | Path) -> ImportNodeState:
    """以给定路径创建状态并执行 node_entry。"""
    return node_entry(create_state(task_id=TASK_ID, origin_file_path=str(path)))


# --------------------------------------------------------------------------- #
# 文件不存在 / 不支持类型: 终止流程, 不抛异常
# --------------------------------------------------------------------------- #
def test_missing_file_returns_original_state(tmp_path: Path):
    missing = tmp_path / "not-exist.md"
    state = create_state(task_id=TASK_ID, origin_file_path=str(missing))

    result = node_entry(state)

    assert result is state  # 原样返回, 不新建状态对象
    assert result["doc_type"] == DocType.UNKNOWN
    assert result["markdown_file_path"] == ""


def test_unsupported_txt_yields_unknown(sample_txt: Path):
    result = _run(sample_txt)

    assert result["doc_type"] == DocType.UNKNOWN
    assert result["markdown_file_path"] == ""


# --------------------------------------------------------------------------- #
# 支持类型: 识别 doc_type, Markdown 额外补全文件路径
# --------------------------------------------------------------------------- #
def test_markdown_sets_doc_type_and_markdown_path(sample_md: Path):
    result = _run(sample_md)

    assert result["doc_type"] == DocType.MARKDOWN
    assert result["markdown_file_path"] == str(sample_md)
    # 存 str 而非 Path, 与 node_pdf_to_md 的写入保持一致
    assert isinstance(result["markdown_file_path"], str)


def test_pdf_sets_doc_type_only(sample_pdf: Path):
    result = _run(sample_pdf)

    assert result["doc_type"] == DocType.PDF
    assert result["markdown_file_path"] == ""


# --------------------------------------------------------------------------- #
# 后缀大小写与别名
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("suffix", ["md", "MD", "markdown"])
def test_markdown_extension_variants(tmp_path: Path, suffix: str):
    file = tmp_path / f"doc.{suffix}"
    file.write_text("# hi", encoding="utf-8")

    result = _run(file)

    assert result["doc_type"] == DocType.MARKDOWN
    assert result["markdown_file_path"] == str(file)
