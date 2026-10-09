"""单元测试: src/utils/markdown_splitter.py

被测对象:
    markdown_split_by_title    按 Markdown 标题层级切分, 生成 level + title_stack

重点覆盖 title_stack 的层级语义:
    - title_stack 按下标对齐标题层级 (下标 i 对应第 i+1 级标题)
    - 缺失的层级用 None 占位, 而不是把下一级标题挤到前面
    - 同级标题替换, 而不是追加成父子关系
"""

from __future__ import annotations

from utils.markdown_splitter import markdown_split_by_title


def _stacks(md: str) -> list[list[str | None]]:
    return [c["title_stack"] for c in markdown_split_by_title(md)]


def test_all_level2_headings_are_siblings():
    """全二级标题时, 每个 chunk 的 stack 应是 [None, 标题], 而不是逐级嵌套。"""
    md = "\n".join(
        [
            "封面内容",
            "",
            "## 安全手册",
            "",
            "安全手册正文",
            "",
            "## 安全标识",
            "",
            "安全标识正文",
            "",
            "## 控制与端口",
            "",
            "控制与端口正文",
        ]
    )

    stacks = _stacks(md)

    assert stacks == [
        [],
        [None, "安全手册"],
        [None, "安全标识"],
        [None, "控制与端口"],
    ]


def test_nested_headings_build_deep_stack():
    """一级 + 二级 + 三级标题应逐级堆叠。"""
    md = "\n".join(
        [
            "# 第一章",
            "",
            "一级正文",
            "",
            "## 1.1",
            "",
            "二级正文",
            "",
            "### 1.1.1",
            "",
            "三级正文",
        ]
    )

    stacks = _stacks(md)

    assert stacks == [
        ["第一章"],
        ["第一章", "1.1"],
        ["第一章", "1.1", "1.1.1"],
    ]


def test_same_level_heading_replaces_sibling():
    """同级的后一个标题应替换前一个, 而不是追加。"""
    md = "\n".join(
        [
            "# A",
            "",
            "a",
            "",
            "# B",
            "",
            "b",
        ]
    )

    stacks = _stacks(md)

    assert stacks == [["A"], ["B"]]


def test_demotion_drops_deeper_levels():
    """从三级回到一级后, 更深的层级要被裁掉, 只保留一级标题。"""
    md = "\n".join(
        [
            "# A",
            "",
            "a",
            "",
            "## A.1",
            "",
            "a1",
            "",
            "# B",
            "",
            "b",
        ]
    )

    stacks = _stacks(md)

    assert stacks == [["A"], ["A", "A.1"], ["B"]]


def test_level_skips_deeper_level_with_none_placeholder():
    """直接从一级跳到三级时, 缺失的二级用 None 占位。"""
    md = "\n".join(
        [
            "# A",
            "",
            "a",
            "",
            "### A.1.1",
            "",
            "a11",
        ]
    )

    stacks = _stacks(md)

    assert stacks == [["A"], ["A", None, "A.1.1"]]


def test_empty_section_produces_no_chunk():
    """标题后没有正文时, 不应产生空 chunk。"""
    md = "\n".join(
        [
            "## 操作指导",
            "",
            "## 数值保持按键HOLD",
            "",
            "正文",
        ]
    )

    chunks = markdown_split_by_title(md)

    assert [(c["level"], c["title_stack"]) for c in chunks] == [
        (2, [None, "数值保持按键HOLD"]),
    ]
