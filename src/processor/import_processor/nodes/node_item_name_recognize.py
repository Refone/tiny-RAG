from pathlib import Path

from utils.node_utils import trace_node, step_log
from utils.logging_utils import logger, brief_list, brief_dict
from processor.import_processor.state import ImportNodeState
from common.prompt.prompt_recognize_item_name import PromptRecognizeItemName
from common.model import LLM, EMBEDDING
from common.client import MILVUS_CLIENT
from common.config.env_config import ENV_CONFIG


@step_log(desc="校验并获取数据")
def step_1_validate_and_get_data(state: ImportNodeState) -> tuple[str, str]:
    file_title = state["file_title"]
    if not file_title:
        raise ValueError("file_title is missing in the state")

    md_path = Path(state["markdown_file_path"])
    if not md_path or not md_path.exists():
        raise ValueError(f"Markdown file does not exist at path: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    return md_content, file_title


@step_log(desc="调用大语言模型识别 item_name")
def step_2_call_llm_return_item_name(md_content: str, file_title: str) -> str:
    # 这里调用大语言模型的逻辑，返回识别出的 item_name
    # 目前用占位符返回
    prompt = PromptRecognizeItemName(
        file_title=file_title, md_content=md_content
    ).prompt

    item_name = LLM.invoke(prompt)

    if not item_name or not item_name.content:
        item_name = (
            file_title  # 如果 LLM 没有返回有效的 item_name，则使用文件标题作为默认值
        )
    else:
        item_name = item_name.content

    return item_name


@step_log(desc="将识别出的 item_name 插入到 Milvus 中")
def step_3_insert_item_name(item_name: str, file_title: str) -> None:
    collection_name = ENV_CONFIG.milvus.collection_item_name

    MILVUS_CLIENT.delete(
        collection_name=collection_name,
        filter=f"file_title == '{file_title}'",
    )

    vecs = EMBEDDING.embed([item_name])
    dense_vector = vecs[0]["dense"]
    sparse_vector = vecs[0]["sparse"]

    ret = MILVUS_CLIENT.insert(
        collection_name=collection_name,
        data=[
            {
                "file_title": file_title,
                "item_name": item_name,
                "dense_vector": dense_vector,
                "sparse_vector": sparse_vector,
            }
        ],
    )

    logger.success(
        f"主体向量插入 Milvus 完成\n"
        f"item_name:['{item_name}'] file_title:['{file_title}']\n"
        f"dense_vector:['{brief_list(dense_vector)}'](len={len(dense_vector)})\n"
        f"sparse_vector:['{brief_dict(sparse_vector)}'](len={len(sparse_vector)})\n"
        f"ret:['{ret}']"
    )


@trace_node(desc="主体识别")
def node_item_name_recognize(state: ImportNodeState) -> ImportNodeState:

    # 校验以及获取数据
    md_content, file_title = step_1_validate_and_get_data(state)

    # 调用大语言模型识别 item_name
    item_name = step_2_call_llm_return_item_name(md_content, file_title)

    # 将识别出的 item_name 插入到 Milvus 中
    step_3_insert_item_name(item_name, file_title)

    state["item_name"] = item_name

    return state


if __name__ == "__main__":
    from rich import print as rprint
    from processor.import_processor.state import load_state, save_state
    from utils.path_utils import PROJECT_ROOT

    prev_state = load_state(
        str(PROJECT_ROOT / "output/tmp/import_04_document_split.json")
    )
    next_state = node_item_name_recognize(prev_state)

    rprint(next_state)

    new_state_json = str(PROJECT_ROOT / "output/tmp/import_05_item_name_recognize.json")
    save_state(next_state, new_state_json)
    logger.info(f"主体识别完成")
    logger.info(f"状态保存路径: {new_state_json}")
    logger.info(f"识别出的主体: {next_state['item_name']}")
