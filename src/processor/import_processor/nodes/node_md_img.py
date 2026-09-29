import base64
from pathlib import Path
import re
from typing import List, TypedDict

from langchain.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

from common.config.app_config import APP_CONFIG
from common.model.vlm import RATE_LIMITER, VLM, encode_image
from common.prompt.load_prompt import load_prompt
from processor.import_processor.state import ImportNodeState, create_state
from utils.markdown_utils import extract_surrounding_context, find_image_position
from utils.path_utils import PROJECT_ROOT
from utils.node_utils import trace_node, step_log
from utils.logging_utils import logger

"""
    "task_id": -,
    "doc_type": -,
    "origin_file_path": -,
    "markdown_file_path": md 文件路径,
    "file_title": 文件标题(不含后缀),
    "md_content": "",
    "item_name": "",
    "chunks": [],
"""
@trace_node(desc="图片处理")
def node_md_img(state: ImportNodeState) -> ImportNodeState:
    """
    图片处理节点 (生成图片的文字描述信息)

    1. 扫描 Markdown 中的图片连接
    2. 讲图片上传至 MinIO 对象存储
    3. (可选) 调用多模态模型生成图片描述
    4. 替换 Markdown 中的图片连接为 MinIO URL
    """
    # 1. 状态校验
    md_content, md_path, img_dir = step_1_validate_and_load_data(state)

    image_info_list = step_2_scan_images(md_content, img_dir)

    summary_dict = step_3_image_summary(image_info_list, state)

    return state

@step_log(desc="检验文件并加载")
def step_1_validate_and_load_data(state) -> tuple[str, Path, Path | None]:
    md_path = state.get("markdown_file_path")
    if not md_path:
        raise ValueError("Markdown 文件路径不存在")

    md_path = Path(md_path)

    if not md_path.exists():
        raise FileNotFoundError(f"Markdown 文件不存在: {md_path}")

    md_content = md_path.read_text(encoding="utf-8")

    img_dir = md_path.parent / "images" # 依赖 MinerU zip 包解包结果
    if not img_dir.exists():
        img_dir = None

    return md_content, md_path, img_dir

class ImageInfo(TypedDict):
    """
    Markdown 中一张图片的相关信息
    """
    # 图片名称
    name: str
    # 图片文件路径
    path: Path
    # 图片描述 ![]() 在 Markdown 中的起始位置|结束为止
    start: int
    end: int
    # 图片描述前后的文字内容
    pre_text: str
    post_text: str

@step_log(desc="扫描图片文件夹图片")
def step_2_scan_images(md_content: str, img_dir: Path) -> List[ImageInfo]:
    image_info_list = []
    if not img_dir:
        return image_info_list

    for image_path in img_dir.iterdir():
        image_suffix = image_path.suffix.lower().lstrip(".")
        if not image_suffix in APP_CONFIG.support_image_format:
            continue

        image_name = image_path.name

        # 获取图片描述符在 Markdown 中的位置
        # 一般来说, md 里面不会有两张一样的图, 如果有, 仅取第一次也是合理的.
        pos = find_image_position(md_content, image_name)
        if not pos:
            # 仅出现在 images 文件夹中, 没有出现在 markdown 文字中
            continue
        start, end = pos

        pre_text, post_text = extract_surrounding_context(md_content, start, end)

        logger.debug(f"{image_name} 图片描述符位置: [{start}, {end}],\n前文字: [{pre_text}]\n后文字[{post_text}]")
        image_info_list.append(
            ImageInfo(
                name=image_name,
                path=image_path,
                start=start,
                end=end,
                pre_text=pre_text,
                post_text=post_text,
                )
            )
    return image_info_list

@step_log(desc="调用 VLM 获取图像摘要")
def step_3_image_summary(image_info_list: List[ImageInfo], state: ImportNodeState) -> dict[str, str]:
    """
    调用 VLM 获取图像摘要
    Args:
        image_info_list (List[ImageInfo]): 图片信息列表
        img_dir (Path): 图片文件夹路径
    Returns:
        dict[str, str]: { "<图片路径>" : "描述摘要" }
    """
    summary_dict: dict[str, str] = {}

    for image_info in image_info_list:
        prompt = load_prompt(
            prompt_template="image_summary",
            md_title=state.get("file_title"),
            pre_text=image_info["pre_text"],
            post_text=image_info["post_text"],
        )

        image_path = image_info["path"]

        message = HumanMessage(
            content=[
                {"type" : "text", "text" : prompt },
                {
                    "type" : "image_url",
                    "image_url": {"url": encode_image(image_path)},
                }
            ]
        )

        chains = VLM | StrOutputParser()
        RATE_LIMITER.acquire()  # 限速
        image_summary = chains.invoke([message])

        summary_dict[str(image_info["path"])] = image_summary
        logger.debug(f"{image_path} 图片摘要: {image_summary}")

    return summary_dict


if __name__ == "__main__":
    from rich import print as rprint

    start = create_state(
        task_id="node_md_img_test",
        markdown_file_path=PROJECT_ROOT / "output/markdown-folder/hak180产品安全手册/hak180产品安全手册.md",
        file_title="hak180产品安全手册",
    )
    end = node_md_img(start)

    rprint(end)