import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from pymilvus.orm.constants import BATCH_SIZE

from utils.logging_utils import logger
from utils.node_utils import trace_node, step_log
from utils.markdown_splitter import Chunk
from common.model import EMBEDDING
from common.client import MILVUS_CLIENT
from common.config.env_config import ENV_CONFIG
from processor.import_processor.state import ImportNodeState

BATCH_SIZE = ENV_CONFIG.embedding.batch_size


@step_log(desc="验证状态并获取文件标题、项目名称和切片列表")
def step_1_validate_and_get_data(
    state: ImportNodeState,
) -> tuple[str, str, list[Chunk]]:
    """
    验证状态并获取文件标题、项目名称和切片列表

    Args:
        state (ImportNodeState): 当前节点的状态

    Returns:
        tuple[str, str, list[Chunk]]: 文件标题、项目名称和切片列表
    """

    chunks_path = Path(state["chunks_json_path"])
    if not chunks_path or not chunks_path.exists() or not chunks_path.is_file():
        raise FileNotFoundError("切片文件不存在")

    chunks_list = list(
        map(lambda x: Chunk(**x), json.loads(chunks_path.read_text(encoding="utf-8")))
    )

    file_title = state["file_title"]
    if not file_title:
        raise ValueError("状态异常: file_title 缺失")

    item_name = state["item_name"]
    if not item_name:
        raise ValueError("状态异常: item_name 缺失")

    return file_title, item_name, chunks_list


def _format_chunk_content(chunk: Chunk) -> str:
    """
    将单个文档切片转换为字符串表示，包含标题层级和内容

    Args:
        chunk (Chunk): 单个文档切片

    Returns:
        str: 切片的字符串表示

    Example:
        {
            "title_stack": ["Chapter 1", "Section 1.1"],
            "content": "This is the content."
        }
        ->
        # Chapter 1
        ## Section 1.1
        This is the content.
    """
    lines = []
    for i, title in enumerate(chunk.get("title_stack", [])):
        if title:
            lines.append("#" * (i + 1) + " " + title)
    lines.append(chunk["content"])
    return "\n".join(lines)


@step_log(desc="文档切片向量化")
def step_2_vect_chunks(chunks_list: list[Chunk]) -> list[dict[str, Any]]:
    """
    对文档切片进行向量化

    Args:
        chunks_list (list[Chunk]): 文档切片列表

    Returns:
        list[dict[str, Any]]: 与切片按下标一一对应的向量数据,
        每个元素含 "content" / "dense" / "sparse" 三个键。
    """

    if not chunks_list:
        logger.warning("切片列表为空")
        return []

    batches: list[list[str]] = [
        [_format_chunk_content(chunk) for chunk in chunks_list[i : i + BATCH_SIZE]]
        for i in range(0, len(chunks_list), BATCH_SIZE)
    ]

    with ThreadPoolExecutor(max_workers=ENV_CONFIG.embedding.concurrency) as pool:
        vecs_list = list(pool.map(EMBEDDING.embed, batches))

    embedded: list[dict[str, Any]] = []
    for batch_texts, batch_vecs in zip(batches, vecs_list):
        if len(batch_vecs) != len(batch_texts):
            raise ValueError(
                f"向量化结果数量与切片数量不一致: "
                f"切片数={len(batch_texts)}, 向量数={len(batch_vecs)}"
            )
        for text, vec in zip(batch_texts, batch_vecs):
            embedded.append(
                {
                    "content": text,
                    "dense": vec["dense"],
                    "sparse": vec["sparse"],
                }
            )

    return embedded


@step_log(desc="向量化切片写入 Milvus")
def step_3_chunk_upsert_milvus(
    file_title: str, item_name: str, embedded: list[dict[str, Any]]
) -> None:
    """
    将已向量化的切片写入 Milvus

    先删除旧数据再写入, 保证重复导入是覆盖而不是丢失。

    Args:
        file_title (str): 文件标题
        item_name (str): 项目名称
        embedded (list[dict[str, Any]]): 切片向量数据,
        每个元素含 "content" / "dense" / "sparse" 三个键。

    Returns:
        None
    """

    if not embedded:
        logger.warning("切片向量列表为空, 直接跳过此步骤")
        return

    # 首先根据 file_title 删除旧数据
    collection_name = ENV_CONFIG.milvus.collection_chunks
    MILVUS_CLIENT.delete(
        collection_name=collection_name,
        filter=f"file_title == '{file_title}'",
    )

    written = 0
    ret = MILVUS_CLIENT.insert(
        collection_name=collection_name,
        data=[
            {
                "file_title": file_title,
                "item_name": item_name,
                "chunk_content": chunk["content"],
                "dense_vector": chunk["dense"],
                "sparse_vector": chunk["sparse"],
            }
            for chunk in embedded
        ],
    )

    insert_count = ret.get("insert_count", 0)
    if insert_count != len(embedded):
        raise RuntimeError(
            f"写入 Milvus 条数不一致: 预期={len(embedded)}, 实际={insert_count}"
        )
    written += insert_count

    logger.success(
        f"切片向量写入 Milvus 完成\n"
        f"file_title:['{file_title}'] item_name:['{item_name}']\n"
        f"collection:['{collection_name}'] 切片数:[{written}]"
    )


@trace_node(desc="切片向量化")
def node_chunks_vect(state: ImportNodeState) -> ImportNodeState:
    """
    文档切片向量化
    """

    # 1. 数据校验、获取必要数据。从文件中读取 chunks 原数据
    file_title, item_name, chunks_list = step_1_validate_and_get_data(state)

    # 2. 对 chunks 进行向量化处理
    embedded = step_2_vect_chunks(chunks_list)

    # 3. 将向量化后的切片写入 Milvus
    step_3_chunk_upsert_milvus(file_title, item_name, embedded)

    return state


if __name__ == "__main__":
    from rich import print as rprint
    from processor.import_processor.state import load_state, save_state
    from utils.path_utils import PROJECT_ROOT

    prev_state = load_state(
        str(PROJECT_ROOT / "output/tmp/import_05_item_name_vect.json")
    )
    next_state = node_chunks_vect(prev_state)

    rprint(next_state)

    new_state_json = str(PROJECT_ROOT / "output/tmp/import_06_chunks_vect.json")
    save_state(next_state, new_state_json)
    logger.info(f"切片向量化完成")
    logger.info(f"状态保存路径: {new_state_json}")
