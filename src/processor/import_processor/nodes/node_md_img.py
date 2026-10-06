import asyncio
from pathlib import Path
import re
from typing import TypedDict

from langchain.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

from common.client.minio_client import get_minio_client
from common.config.app_config import APP_CONFIG
from common.config.env_config import ENV_CONFIG
from common.model.vlm import RATE_LIMITER, VLM, encode_image
from common.prompt.load_prompt import load_prompt
from processor.import_processor.state import ImportNodeState, create_state
from utils.markdown_utils import extract_surrounding_context, find_image_position
from utils.path_utils import PROJECT_ROOT
from utils.node_utils import trace_node, step_log
from utils.logging_utils import logger

_MD_FIXED_SUFFIX = "_fixed"

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

@step_log(desc="检验文件并加载")
def step_1_validate_and_load_data(state: ImportNodeState) -> tuple[Path, str, str]:
    file_title = state.get("file_title")
    if not file_title:
        raise ValueError("文件标题不存在")

    md_path = state.get("markdown_file_path")
    if not md_path:
        raise ValueError("Markdown 文件路径不存在")

    md_path = Path(md_path)

    if not md_path.exists():
        raise FileNotFoundError(f"Markdown 文件不存在: {md_path}")

    md_content = md_path.read_text(encoding="utf-8")

    logger.info(f"加载 Markdown 文件成功: {md_path}, 文件标题: {file_title}")
    return md_path, md_content, file_title


@step_log(desc="扫描图片文件夹图片")
def step_2_scan_images(
    md_path: Path,
    md_content: str,
    ) -> list[ImageInfo]:

    image_info_list = []

    img_dir = md_path.parent / "images"
    if not img_dir.exists():
        logger.info(f"图片文件夹不存在: {img_dir}")
        return image_info_list

    # rglob("*") 会递归遍历所有层级的文件/文件夹
    for image_path in img_dir.rglob("*"):
        if not image_path.is_file():
            continue

        image_suffix = image_path.suffix.lower().lstrip(".")
        if image_suffix not in APP_CONFIG.support_image_format:
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

        logger.debug(
            f"{image_name} 内联图片描述位置: [{start}, {end}],\n"
            f"前文字: [{pre_text}]\n后文字[{post_text}]"
        )
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

@step_log(desc="异步并发请求 VLM 获取图像摘要")
async def step_3_image_summary(
    file_title: str,
    image_info_list: list[ImageInfo],
    ) -> dict[str, str]:
    """
    请求 VLM 获取图像摘要

    Args:
        file_title: 文件标题
        image_info_list (list[ImageInfo]): 图片信息列表
    Returns:
        dict[str, str]: { "<图片名>" : "描述摘要" }
    """
    chains = VLM | StrOutputParser()
    sem = asyncio.Semaphore(APP_CONFIG.vlm_max_concurrent_requests)

    # 异步处理单张图片的函数
    async def process_image(image_info: ImageInfo) -> tuple[str, str]:
        prompt = load_prompt(
            prompt_template="image_summary",
            md_title=file_title,
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

        async with sem:
            await RATE_LIMITER.acquire()  # 限速
            result = image_info["name"], await chains.ainvoke([message])
            logger.debug(f"{image_path} 图片摘要: {result[1]}")
            return result

    # 并发处理所有图片
    futures = [process_image(image_info) for image_info in image_info_list]
    results = await asyncio.gather(*futures)

    return dict(results)

@step_log("图片上传 Minio")
def step_4_upload_images_get_url(
    file_title: str,
    image_info_list: list[ImageInfo],
    ) -> dict[str, str]:
    """
    上传图片至 Minio

    Args:
        file_title: 文件标题
        image_info_list: list[ImageInfo] 图片信息列表
    returns:
        dict[str, str]: (<图片名> : url)
    """

    image_url_dict = {}
    minio_client = get_minio_client()
    prefix = ENV_CONFIG.minio.image_dir + "/" + file_title

    # 查询 MinIO 中是否已经存在同名文件夹, 若存在, 直接删除(同名则覆盖原则)
    del_cnt = minio_client.clear_dir_if_exist(prefix)
    if del_cnt > 0:
        logger.info(f"{prefix} 覆盖删除 {del_cnt} 张图片")

    # 依次上传图片
    for image in image_info_list:
        try:
            url = minio_client.upload_file(
                prefix=prefix,
                as_name=image["name"],
                file_path=image["path"]
            )
            image_url_dict[image["name"]] = url
            logger.debug(f"{image['name']} 上传成功: {url}")
        except Exception as e:
            logger.warning(f"{image['name']} 上传失败, 跳过. error: {e}")

    return image_url_dict

@step_log("替换 markdown 中的图片标记")
def step_5_md_content_image_replace(
    md_content: str,
    image_summary_dict: dict[str, str],
    image_url_dict: dict[str, str],
    ) -> str:
    """
    对 md 文件图片标记进行替换      ![](本地路径) -> ![摘要](网络地址)

    Args:
        md_content: str  markdown 文件内容
        image_summary_dict: dict[str, str]  {"图片名":"图片摘要"}
        image_url_dict: dict[str, str]  {"图片名", "url"}
    Returns:
        str: 替换后的 markdown 内容
    """
    cnt = 0
    fixed_content = md_content

    for image_name, summary in image_summary_dict.items():
        url = image_url_dict.get(image_name)
        reg = re.compile(r"\!\[.*?\]\(.*?" + re.escape(image_name) + r".*?\)")

        fixed_content = reg.sub(lambda _: f"![{summary}]({url})", fixed_content)
        cnt += 1

    logger.info(f"完成文档中 {cnt} 处替换")

    return fixed_content

@step_log("保存修改后的 markdown")
def step_6_new_content_to_disk(md_path: Path, md_content: str) -> Path:
    """
    保存修改后的 markdown 文件到磁盘

    Args:
        md_path: Path  原始 markdown 文件路径
        md_content: str  修改后的 markdown 内容
    Returns:
        Path: 修改后的 markdown 文件路径
    """

    fixed_md_path: Path = md_path.with_name(f"{md_path.stem}{_MD_FIXED_SUFFIX}.md")
    fixed_md_path.write_text(encoding="utf-8", data=md_content)

    logger.info(f"图片标注修正后的内容已写入 {str(fixed_md_path)}")

    return fixed_md_path

@trace_node(desc="Markdown 内联图片语法处理")
def node_md_img(state: ImportNodeState) -> ImportNodeState:
    """
    图片处理节点 (生成图片的文字描述信息)
    """

    # 1. 状态校验
    md_path, md_content, file_title = step_1_validate_and_load_data(state)

    # 2. 扫描 images 目录, 获取图片信息列表
    image_info_list = step_2_scan_images(md_path, md_content)

    # 3. 请求 VLM 获取图片摘要
    # {"<图片名>" : "<摘要>"}
    summary_dict = asyncio.run(step_3_image_summary(file_title, image_info_list))

    # 4. 上传图片至 MinIO 并获取 URL
    # {"<图片名>" : "<URL>"}
    url_dict = step_4_upload_images_get_url(file_title, image_info_list)

    # 5. 替换 Markdown 中的内联图片
    # ![](local_url) -> ![abstract](minio_url)
    fixed_md_content = step_5_md_content_image_replace(md_content, summary_dict, url_dict)

    # 6. 将新的 Markdown 内容写入磁盘
    fixed_md_path = step_6_new_content_to_disk(md_path, fixed_md_content)

    state["markdown_file_path"] = str(fixed_md_path)

    return state

if __name__ == "__main__":
    from rich import print as rprint
    from processor.import_processor.state import load_state, save_state

    prev_state = load_state(str(PROJECT_ROOT / "output/tmp/import_02_pdf_to_md.json"))
    next_state = node_md_img(prev_state)

    rprint(next_state)

    new_state_json = str(PROJECT_ROOT / "output/tmp/import_03_md_img.json")
    save_state(next_state, new_state_json)
    logger.info(f"Markdown 内联图片处理完成")
    logger.info(f"状态保存路径: {new_state_json}")
    logger.info(f"修改后的 Markdown 文件路径: {next_state['markdown_file_path']}")