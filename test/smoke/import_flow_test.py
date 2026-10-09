"""冒烟测试: 导入流程 (processor.import_processor.main_graph.import_processor)。

覆盖范围:
    当前导入流程中, 只有 node_entry 与 node_pdf_to_md 有真实实现;
    其余节点 (node_md_img / node_document_split / node_item_name_vect /
    node_bge_embedding / node_upsert_milvus) 均为 stub, 仅原样透传 state。

    本测试「测已有功能 + 验证链路路径」:
    - Markdown: 不依赖外部服务, 全链路 invoke, 校验入口识别的
      markdown_file_path 能一路透传到最终 state。
    - PDF: 真实调用 MinerU 完成 pdf -> md 转换, 校验转换结果写回 state。
    - 两种文档类型都会断言「实际走过的节点链」与预期一致, 以此确认
      路由分支正确、stub 节点没有破坏链路。

运行方式 (-s 关闭输出捕获让 loguru 日志实时打印, -v 显示用例名而非 '.'):
    uv run pytest test/smoke -s -v                    # 只跑 Markdown 冒烟 (无网络)
    uv run pytest test/smoke -s -v --run-smoke        # 连同 PDF 冒烟 (需 MinerU Key)

日志说明:
    节点的执行日志由 loguru 写到 stdout; pytest 默认捕获 stdout/stderr,
    只在用例失败时才回放, 因此不带 -s 跑「过程日志」看不见。test/smoke/conftest.py
    用 pytest_runtest_call hook 给每个用例包横幅并把 loguru 异步日志 flush 成一段。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from common.enum.doc_type import DocType
from processor.import_processor.main_graph import import_processor
from processor.import_processor.state import create_state
from utils import task_utils

TASK_ID = "import-flow-smoke"

# 期望的节点执行链 (按拓扑顺序; 两种文档类型只在入口后的第二个节点分叉)
MD_CHAIN = [
    "node_entry",
    "node_md_img",
    "node_document_split",
    "node_item_name_vect",
    "node_bge_embedding",
    "node_upsert_milvus",
]

PDF_CHAIN = [
    "node_entry",
    "node_pdf_to_md",
    "node_md_img",
    "node_document_split",
    "node_item_name_vect",
    "node_bge_embedding",
    "node_upsert_milvus",
]


def _invoke(origin_file_path: Path) -> dict:
    """以给定文件路径创建初始状态, 全链路执行导入流程图并返回最终状态。"""
    initial_state = create_state(
        task_id=TASK_ID,
        origin_file_path=str(origin_file_path),
    )
    return import_processor.invoke(initial_state)


def test_markdown_import_flow(sample_md: Path):
    """Markdown 冒烟: 不转换, 入口识别后直接复用原文件路径并透传到底。"""
    final = _invoke(sample_md)

    # 已实现功能: 入口识别为 markdown, 并把原文件路径写回 markdown_file_path
    assert final["doc_type"] == DocType.MARKDOWN
    assert final["markdown_file_path"] == str(sample_md)

    # 未实现节点均为 stub, 不应擅自改动其余字段
    assert final["md_content"] == ""
    assert final["item_name"] == ""
    assert final["chunks"] == []

    # 链路路径正确: 跳过 pdf 转换分支, 直接进入图片处理及后续 stub 链
    assert task_utils.get_task_done_nodes(TASK_ID) == MD_CHAIN


@pytest.mark.smoke
def test_pdf_import_flow(sample_pdf: Path):
    """PDF 冒烟: 真实调用 MinerU 把 pdf 转成 md, 并校验转换结果写回 state。

    依赖外部服务 MinerU (需要 .env 配置 MINERU_* 且网络可达),
    故标注 @pytest.mark.smoke, 默认跳过, 用 --run-smoke 开启。
    """
    final = _invoke(sample_pdf)

    # 已实现功能: 入口识别为 pdf, node_pdf_to_md 产出真实的 md 文件
    assert final["doc_type"] == DocType.PDF
    assert final["file_title"] == sample_pdf.stem

    md_path = final["markdown_file_path"]
    assert md_path, "markdown_file_path 不应为空"
    assert Path(md_path).is_file(), f"转换后的 md 文件应真实存在: {md_path}"

    # 链路路径正确: 先 pdf 转换, 再进入与 markdown 相同的后续 stub 链
    assert task_utils.get_task_done_nodes(TASK_ID) == PDF_CHAIN
