from utils.logging_util import node_log
from processor.import_processor.state import ImportGraphState

@node_log("node_md_img")
def node_md_img(state: ImportGraphState) -> ImportGraphState:
    """
    图片处理节点 (生成图片的文字描述信息)

    TODO:
    1. 扫描 Markdown 中的图片连接
    2. 讲图片上传至 MinIO 对象存储
    3. (可选) 调用多模态模型生成图片描述
    4. 替换 Markdown 中的图片连接为 MinIO URL
    """
    return state