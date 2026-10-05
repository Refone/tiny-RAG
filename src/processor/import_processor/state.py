import copy
from typing import TypedDict

from common.enum.doc_type import DocType

class ImportNodeState(TypedDict, total=False):
    """
    导入图状态

    注意: 这是整个导入流程的「唯一事实来源」。
    任何节点需要读写新字段时, 必须先在这里声明,
    否则 LangGraph 会静默丢弃未声明的 key (不报错) 。

    TODO: 考虑到 Graph State 可能需要做 持久化 和 跨平台,
          故最好使用原生数据结构, 以便正常序列化。
          所以路径保持 str, 而非 Path,
          枚举类型最好也不要用 StrEnum
    """
    # 任务 ID
    task_id: str

    # 文件类型
    doc_type: DocType

    # 原始文件路径, 不确定文件格式
    origin_file_path: str

    # (转换后的) markdown 文件路径
    markdown_file_path: str

    # 文件名 (不含后缀)
    file_title: str

    # PDF 转换后的 markdown 全文 (node_pdf_to_md 产出)
    md_content: str

    # 文档主体识别结果, 如 "iPhone 13" (node_item_name_recognize 产出)
    item_name: str

    # 切分后的 chunk 列表 (node_document_split 产出)
    chunks: list[dict[str, any]]


__default_state: ImportNodeState = {
    "task_id": "",
    "doc_type": DocType.UNKNOWN,
    "origin_file_path": "",
    "markdown_file_path": "",
    "file_title": "",
    "md_content": "",
    "item_name": "",
    "chunks": [],
}

# 合法字段集合, 用于在 create_state 时校验入参, 防止拼写错误被 LangGraph 静默丢弃
_ALLOWED_KEYS = frozenset(ImportNodeState.__optional_keys__) | frozenset(
    ImportNodeState.__required_keys__
)


def create_state(**state_dict) -> ImportNodeState:
    unknown = set(state_dict) - _ALLOWED_KEYS
    if unknown:
        raise KeyError(
            f"创建状态时传入了未声明的字段: {sorted(unknown)}; "
            f"合法字段: {sorted(_ALLOWED_KEYS)}"
        )
    state = copy.deepcopy(__default_state)
    state.update(state_dict)
    return state


def get_default_state() -> ImportNodeState:
    return copy.deepcopy(__default_state)


if __name__ == '__main__':
    from rich import print as rprint

    state = create_state(
        task_id="1234",
        doc_type=DocType.MARKDOWN,
        origin_file_path="/path/to/xxx.md",
    )
    rprint(state)

    try:
        create_state(not_a_field=1)
    except KeyError as e:
        rprint(f"[red]key 校验生效: {e}[/red]")
