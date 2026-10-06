import json
from pathlib import Path

from common.config.app_config import APP_CONFIG
from utils.node_utils import trace_node, step_log
from processor.import_processor.state import ImportNodeState
from utils.markdown_splitter import split_markdown, Chunk
from utils.logging_utils import logger

@step_log(desc="验证并获取数据")
def step_1_validate_and_get_data(state: ImportNodeState) -> tuple[Path, str, str]:
    """
    验证并获取 Markdown 文件路径、内容和文件标题

    Returns:
        tuple[Path, str, str]: Markdown 文件路径、内容和文件标题
    """

    md_path = state.get("markdown_file_path")
    md_path = Path(md_path)
    if (not md_path) or (not md_path.is_file()):
        raise ValueError(f"Markdown 文件路径为空或文件不存在 ({md_path})")

    file_title = state.get("file_title")

    md_content = md_path.read_text(encoding="utf-8")

    # 跨系统 md 兼容，所有 \r\n, \r, 统一为 \n
    md_content = md_content.replace("\r\n", "\n").replace("\r", "\n")

    return md_path, md_content, file_title

@step_log(desc="切分 Markdown 内容")
def step_2_split_markdown(md_content: str) -> list[Chunk]:
    """
    切分 Markdown 内容为 Chunk 列表

    Args:
        md_content (str): Markdown 内容

    Returns:
        list[Chunk]: 切分后的 Chunk 列表
    """

    chunk_list = split_markdown(
        md_content,
        max_chunk_size=APP_CONFIG.max_chunk_size,
        min_chunk_size=APP_CONFIG.min_chunk_size,
        overlap_size=APP_CONFIG.overlap_size)

    return chunk_list

@step_log(desc="备份切分后的 JSON")
def step_3_backup_chunks_json(
    md_path: Path,
    file_title: str,
    chunks_list: list[Chunk]
    ) -> Path:
    """
    备份切分后的 Markdown 内容为 JSON 文件

    Args:
        md_path (Path): Markdown 文件路径
        file_title (str): 文件标题
        chunks_list (list[Chunk]): 切分后的 Chunk 列表

    Returns:
        Path: 生成的 JSON 文件路径
    """

    chunk_json_path = md_path.parent / f"{file_title}_chunks.json"
    chunk_json_path.write_text(json.dumps(chunks_list, ensure_ascii=False, indent=4), encoding="utf-8")

    logger.info(f"Chunks JSON 保存于 {chunk_json_path}")
    return chunk_json_path

@trace_node(desc="文档切分")
def node_document_split(state: ImportNodeState) -> ImportNodeState:
    """
    文档切分节点

    1. 基于 Markdown 标题层级进行递归切分
    2. 对仍然过长的段落进行二次切分
    3. 生成包含 Metadata 的 Chunk 列表
    """

    # 1. 校验状态并获取数据
    md_path, md_content, file_title = step_1_validate_and_get_data(state)

    # 2. 切分 Markdown 内容
    chunks_list = step_2_split_markdown(md_content)

    # 3. 备份切分后的 JSON
    chunks_json_path = step_3_backup_chunks_json(md_path, file_title, chunks_list)
    state["chunks_json_path"] = str(chunks_json_path)

    return state

if __name__ == "__main__":
    from rich import print as rprint
    from processor.import_processor.state import load_state, save_state
    from utils.path_utils import PROJECT_ROOT

    prev_state = load_state(str(PROJECT_ROOT / "output/tmp/import_03_md_img.json"))
    next_state = node_document_split(prev_state)

    rprint(next_state)

    new_state_json = str(PROJECT_ROOT / "output/tmp/import_04_document_split.json")
    save_state(next_state, new_state_json)
    logger.info(f"文档切分完成")
    logger.info(f"状态保存路径: {new_state_json}")
    logger.info(f"切分后的 chunks 路径: {next_state['chunks_json_path']}")
