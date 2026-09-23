from typing import TypedDict
import copy

class ImportGraphState(TypedDict):
    """
    导入图状态
    """
    task_id: str    # 任务 id
    is_md: bool     # 是否为 markdown 文件
    is_pdf: bool    # 是否为 pdf 文件

    # TODO: 整理这些字段
    local_dir: str  # pdf 转 md 输出的目录
    local_file: str
    local_file_path: str
    file_title: str
    pdf_path: str
    md_path: str

    # --- 切块 ---
    md_content: str
    chunks: list
    item_name: str # 主体名

    # --- 数据库相关 ---
    embeddings_content: list

_graph_default_state = ImportGraphState(
    task_id="",
    is_md=False,
    is_pdf=False,
    local_dir="",
    local_file="",
    local_file_path="",
    file_title="",
    pdf_path="",
    md_path="",
    md_content="",
    chunks=[],
    item_name="",
    embeddings_content=[],
)

def create_default_state(**state_dict) -> ImportGraphState:
    state: ImportGraphState = copy.deepcopy(_graph_default_state)
    state.update(state_dict)
    return state

def get_default_state() -> ImportGraphState:
    return copy.deepcopy(_graph_default_state)

if __name__ == '__main__':
    datadict = {
        "task_id":"1234",
        "is_md":False,
        "is_pdf":False
    }
    test_state: ImportGraphState = create_default_state(**datadict)
    print(test_state)