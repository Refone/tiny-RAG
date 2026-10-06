import json
from pathlib import Path

from utils.node_utils import trace_node, step_log
from processor.import_processor.state import ImportNodeState
from utils.markdown_splitter import split_markdown
from utils.logging_utils import logger

@step_log(desc="验证并获取数据")
def step_1_validate_and_get_data(state):
    md_path = state.get("markdown_file_path")
    md_path = Path(md_path)

    if (not md_path) or (not md_path.is_file()):
        raise ValueError(f"Markdown 文件路径为空或文件不存在 ({md_path})")

    md_content = md_path.read_text(encoding="utf-8")

    # 跨系统 md 兼容，所有 \r\n, \r, 统一为 \n
    md_content = md_content.replace("\r\n", "\n").replace("\r", "\n")

    return md_path, md_content

@step_log(desc="切分 Markdown 内容")
def step_2_split_markdown(md_content):

    chunk_list = split_markdown(md_content, max_chunk_size=1000, overlap_size=100)

    return chunk_list

@step_log(desc="备份切分后的 JSON")
def step_3_backup_chunks_json(md_path, chunks_list):
    chunk_json_path = md_path.parent / f"{md_path.stem}_chunks.json"
    chunk_json_path.write_text(json.dumps(chunks_list, ensure_ascii=False, indent=4), encoding="utf-8")
    logger.info(f"Chunks JSON 保存于 {chunk_json_path}")

@trace_node(desc="文档切分")
def node_document_split(state: ImportNodeState) -> ImportNodeState:
    """
    文档切分节点

    1. 基于 Markdown 标题层级进行递归切分
    2. 对仍然过长的段落进行二次切分
    3. 生成包含 Metadata 的 Chunk 列表
    """

    md_path, md_content = step_1_validate_and_get_data(state)

    chunks_list = step_2_split_markdown(md_content)

    step_3_backup_chunks_json(md_path, chunks_list)

    return state

if __name__ == "__main__":
    start_state = ImportNodeState(
        markdown_file_path=Path("/Users/refone/Coding/shop-assistant/output/markdown-folder/hak180产品安全手册/hak180产品安全手册_fixed.md")
        # md_path=Path("/Users/refone/Coding/shop-assistant/test/test-data/第一章-初识智能体.md")
        )
    node_document_split(start_state)