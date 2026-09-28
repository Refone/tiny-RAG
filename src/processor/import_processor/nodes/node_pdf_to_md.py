"""PDF 转 Markdown 节点: 校验 PDF -> 上传 MinerU 转换 -> 下载并解压结果。

依赖状态字段:
    origin_file_path (str): 待转换 PDF 的绝对路径, step_1 校验其存在性与格式。

更新状态字段:
    file_title (str): PDF 文件名 (不含后缀), step_1 写入, step_3 用于命名结果文件。
    markdown_file_path (str): 转换后 markdown 文件的绝对路径, 节点末尾写回。

三个步骤函数 step_1/2/3 由节点函数 node_pdf_to_md 串联;
所有对外 HTTP 调用集中在本模块 (requests), 便于单元测试统一 mock。
"""

import shutil
import time
from pathlib import Path

import requests

from common.config.settings import config
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import logger
from utils.node_utils import step_log, trace_node
from utils.path_utils import from_project_root

# PDF 文件头魔数 (前 5 字节)
_PDF_MAGIC = b"%PDF-"
# 轮询上限 10min: 依据 MinerU 官方「1 页约 0.5~1s」预估
_POLL_TIMEOUT_SECONDS = 600
# 轮询间隔
_POLL_INTERVAL_SECONDS = 3
# MinerU 下载 markdown 压缩包后解压的目标目录
_MD_UNZIP_FOLDER = "output/markdown-folder"

@step_log("校验 PDF 文件")
def step_1_validate_and_setup(state: ImportNodeState) -> Path:
    """校验原始文件是真实存在的 PDF, 并把文件名(不含后缀)写入 state。"""
    origin = state.get("origin_file_path")
    if not origin:
        raise ValueError(f"origin_file_path 为空: {origin!r}")

    pdf_path = Path(origin)
    if not pdf_path.is_file():
        raise ValueError(f"文件不存在或不是文件: {pdf_path}")

    with pdf_path.open("rb") as f:
        if f.read(len(_PDF_MAGIC)) != _PDF_MAGIC:
            raise ValueError(f"文件不是 PDF 格式: {pdf_path}")

    state["file_title"] = pdf_path.stem
    logger.debug(f"PDF 校验通过: {pdf_path}")
    return pdf_path


@step_log("上传 PDF, 轮询等待转换完成")
def step_2_upload_and_poll(pdf_path: Path) -> str:
    """上传 PDF 到 MinerU 并轮询转换结果, 返回结果包 (zip) 的下载地址。"""
    if not config.mineru.base_url or not config.mineru.api_key:
        raise ValueError("MinerU 配置错误, 请检查 .env 是否正确配置 MINERU_ 相关参数")

    # 配置参考: https://mineru.net/apiManage/docs
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.mineru.api_key}",
    }
    apply_url = f"{config.mineru.base_url}/file-urls/batch"
    payload = {
        "files": [{"name": pdf_path.name, "data_id": pdf_path.stem}],
        "model_version": "vlm",
    }

    apply_resp = requests.post(apply_url, headers=headers, json=payload)
    if apply_resp.status_code != 200:
        raise requests.HTTPError(f"MinerU 上传文件失败: {apply_resp.text}")

    apply_resp_data = apply_resp.json()
    if apply_resp_data["code"] != 0:
        raise requests.RequestException(f"HTTP 请求成功, 但业务逻辑失败: {apply_resp_data['msg']}")

    file_upload_urls = apply_resp_data["data"]["file_urls"]
    batch_id = apply_resp_data["data"]["batch_id"]
    if not file_upload_urls or not batch_id:
        raise requests.RequestException(f"申请上传地址失败: {apply_resp_data['msg']}")

    upload_url = file_upload_urls[0]
    logger.debug(f"申请上传地址成功: batch_id={batch_id}, upload_url={upload_url}")

    # PUT 上传只返回状态码, 无 body
    with requests.Session() as session:

        # 纯净版的请求头,不随意携带代理的参数
        session.trust_env = False

        upload_resp = session.put(upload_url, data=pdf_path.read_bytes())
        if upload_resp.status_code != 200:
            raise requests.RequestException(f"上传文件失败: {upload_resp.text}")

    poll_url = f"{config.mineru.base_url}/extract-results/batch/{batch_id}"
    logger.debug(f"上传文件成功, 轮询 url: {poll_url}")

    start = time.time()
    while True:
        time.sleep(_POLL_INTERVAL_SECONDS)

        if time.time() - start > _POLL_TIMEOUT_SECONDS:
            raise requests.Timeout("转换超时")

        try:
            poll_resp = requests.get(poll_url, headers=headers)
        except Exception:
            logger.debug(f"请求异常, {_POLL_INTERVAL_SECONDS}s 后重试")
            continue

        if poll_resp.status_code != 200:
            logger.debug(f"请求失败, {_POLL_INTERVAL_SECONDS}s 后重试")
            continue

        poll_resp_data = poll_resp.json()
        if poll_resp_data["code"] != 0:
            raise requests.RequestException(f"MinerU 解析失败: {poll_resp_data['msg']}")

        extract_result = poll_resp_data["data"]["extract_result"][0]
        if extract_result["state"] == "done":
            zip_url = extract_result["full_zip_url"]
            if not zip_url:
                raise requests.RequestException(
                    f"MinerU 解析完毕, zip 地址异常: {poll_resp_data['msg']}"
                )
            logger.debug(f"MinerU 解析完毕, zip 地址: {zip_url}")
            return zip_url
        if extract_result["state"] == "failed":
            raise requests.RequestException(f"MinerU 解析失败: {poll_resp_data['msg']}")
        # 仍在处理中, 继续轮询
        logger.debug(f"解析未完成, {_POLL_INTERVAL_SECONDS}s 后重试")


@step_log("下载并解压")
def step_3_download_and_unzip(zip_url: str, state: ImportNodeState) -> Path:
    """下载结果包并解压, 把 full.md 重命名为 <file_title>.md 后返回其路径。"""
    # 在函数内解析目录而非模块级常量: 既让 from_project_root 可被测试 mock,
    # 也避免 import 时机过早固定路径。
    md_dir = from_project_root(_MD_UNZIP_FOLDER)
    md_dir.mkdir(parents=True, exist_ok=True)

    download_response = requests.get(zip_url)
    if download_response.status_code != 200:
        raise requests.RequestException(f"下载 zip 文件失败: {download_response.text}")

    file_title = state["file_title"]
    zip_path = md_dir / f"{file_title}.zip"
    extract_dir = md_dir / file_title

    zip_path.write_bytes(download_response.content)
    if extract_dir.is_dir():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(zip_path, extract_dir)

    full_md = extract_dir / "full.md"
    if not full_md.is_file():
        raise RuntimeError("zip 文件解压后, 没有找到 full.md 文件")

    md_path = full_md.rename(full_md.with_name(f"{file_title}.md"))
    logger.debug(f"下载并解压成功, md 路径: {md_path}")
    return md_path


@trace_node(desc="PDF 转 Markdown")
def node_pdf_to_md(state: ImportNodeState) -> ImportNodeState:
    """串联三步: 校验 PDF -> MinerU 转换 -> 下载解压, 并写回 markdown_file_path。"""
    pdf_path = step_1_validate_and_setup(state)
    zip_url = step_2_upload_and_poll(pdf_path)
    md_path = step_3_download_and_unzip(zip_url, state)

    state["markdown_file_path"] = str(md_path)
    return state


if __name__ == "__main__":
    from rich import print as rprint

    from processor.import_processor.state import create_state

    # 冒烟测试: 需真实 MinerU API Key
    state = create_state(
        task_id="UNIT-TEST:node_pdf_to_md",
        origin_file_path=from_project_root("test/test-data/hak180产品安全手册.pdf"),
    )
    rprint(node_pdf_to_md(state))
