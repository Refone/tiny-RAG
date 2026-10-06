import shutil
import time
from pathlib import Path

import requests

from common.config.env_config import ENV_CONFIG
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import logger
from utils.node_utils import step_log, trace_node
from pypdf import PdfReader

# PDF 文件头魔数 (前 5 字节)
_PDF_MAGIC = b"%PDF-"

def pdf_page_cnt(pdf_path: Path) -> int:
    """获取 PDF 的页数"""
    with pdf_path.open("rb") as f:
        reader = PdfReader(f)
        return len(reader.pages)

@step_log("校验 PDF 文件")
def step_1_validate_and_setup(state: ImportNodeState) -> tuple[Path, int, str]:
    """校验原始文件是真实存在的 PDF, 并把文件名(不含后缀)写入 state。"""
    origin = state.get("origin_file_path")
    if not origin:
        raise ValueError(f"origin_file_path 为空: {origin!r}")
    file_title = Path(origin).stem

    pdf_path = Path(origin)
    if not pdf_path.is_file():
        raise ValueError(f"文件不存在或不是文件: {pdf_path}")

    with pdf_path.open("rb") as f:
        if f.read(len(_PDF_MAGIC)) != _PDF_MAGIC:
            raise ValueError(f"文件不是 PDF 格式: {pdf_path}")

    file_title = state.get("file_title")
    if not state.get("file_title"):
        raise ValueError(f"file_title 为空: {state!r}")

    logger.info(f"PDF 校验通过: {pdf_path}")
    return pdf_path, pdf_page_cnt(pdf_path), file_title

@step_log("上传 PDF, 轮询等待转换完成")
def step_2_upload_and_poll(pdf_path: Path, page_cnt: int) -> str:
    """
    上传 PDF 到 MinerU
    轮询转换结果
    获得转换后的 zip 地址, 并返回。

    四个 HTTP 请求:
        1. apply_xxx    上传申请
        2. upload_xxx   文件上传
        3. poll_xxx     轮询解析结果

        xxx_url:        请求 URL
        xxx_resp:       请求响应
        xxx_resp_data:  请求响应的 JSON 数据

    """

    # 检查 .env 中的相关配置
    if not ENV_CONFIG.mineru.base_url or not ENV_CONFIG.mineru.api_key:
        raise ValueError("MinerU 配置错误, 请检查 .env 是否正确配置 MINERU_ 相关参数")

    # 配置参考: https://mineru.net/apiManage/docs
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {ENV_CONFIG.mineru.api_key}",
    }
    apply_url = f"{ENV_CONFIG.mineru.base_url}/file-urls/batch"
    payload = {
        "files": [{"name": pdf_path.name, "data_id": pdf_path.stem}],
        "model_version": "vlm",
        "is_ocr": True,
    }

    # 1. 上传申请
    apply_resp = requests.post(apply_url, headers=headers, json=payload)
    if apply_resp.status_code != 200:
        raise requests.HTTPError(f"MinerU 上传文件失败: {apply_resp.text}")

    apply_resp_data = apply_resp.json()
    if apply_resp_data["code"] != 0:
        raise requests.RequestException(f"HTTP 请求成功, 但业务逻辑失败: {apply_resp_data['msg']}")

    # 2. 文件上传
    upload_urls = apply_resp_data["data"]["file_urls"]
    batch_id = apply_resp_data["data"]["batch_id"]
    if not upload_urls or not batch_id:
        raise requests.RequestException(f"申请上传地址失败: {apply_resp_data['msg']}")

    upload_url = upload_urls[0]
    logger.debug(f"申请上传地址成功: batch_id={batch_id}, upload_url={upload_url}")

    # PUT 上传只返回状态码, 无 body
    with requests.Session() as session:

        # 纯净版的请求头,不随意携带代理的参数
        session.trust_env = False

        upload_resp = session.put(upload_url, data=pdf_path.read_bytes())
        if upload_resp.status_code != 200:
            raise requests.RequestException(f"上传文件失败: {upload_resp.text}")

    # 3. 轮询解析结果
    poll_url = f"{ENV_CONFIG.mineru.base_url}/extract-results/batch/{batch_id}"
    logger.debug(f"上传文件成功, 轮询 url: {poll_url}")

    # 预计等待时间
    est_time = ENV_CONFIG.mineru.est_per_page * page_cnt
    # 轮询间隔时间
    interval_time = ENV_CONFIG.mineru.poll_interval
    # 最大等待时间
    max_wait_time = ENV_CONFIG.mineru.timeout_per_page * page_cnt

    start = time.time()
    logger.debug(f"预计等待时间: {est_time}s, 轮询间隔: {interval_time}s, 最大等待时间: {max_wait_time}s")
    time.sleep(max(0, est_time - interval_time))
    while True:
        time.sleep(interval_time)

        if time.time() - start > max_wait_time:
            raise requests.Timeout("转换超时")

        try:
            poll_resp = requests.get(poll_url, headers=headers)
        except Exception:
            logger.debug(f"请求异常, {interval_time}s 后重试")
            continue

        if poll_resp.status_code != 200:
            logger.debug(f"请求失败, {interval_time}s 后重试")
            continue

        logger.debug(f"请求成功, 轮询返回: {poll_resp.text}")
        poll_resp_data = poll_resp.json()
        if poll_resp_data["code"] != 0:
            raise requests.RequestException(f"MinerU 解析失败: {poll_resp_data['msg']}")

        extract_result = poll_resp_data["data"]["extract_result"][0]
        if extract_result["state"] == "done":
            zip_url = extract_result["full_zip_url"]
            if not zip_url:
                raise requests.RequestException(f"MinerU 解析完毕, zip 地址异常: {poll_resp_data['msg']}")
            logger.debug(f"MinerU 解析完毕, zip 地址: {zip_url}")
            return zip_url
        elif extract_result["state"] == "failed":
            raise requests.RequestException(f"MinerU 解析失败: {poll_resp_data['msg']}")
        else:
        # 仍在处理中, 继续轮询
            logger.debug(f"解析未完成, {interval_time}s 后重试")


@step_log("下载并解压")
def step_3_download_and_unzip(zip_url: str, file_title: str) -> Path:
    """
    下载结果包并解压
    把 full.md 重命名为 <file_title>.md 后返回其路径。
    """

    # 在函数内解析目录而非模块级常量: 既让 from_project_root 可被测试 mock,
    # 也避免 import 时机过早固定路径。
    md_dir = Path(ENV_CONFIG.mineru.unzip_dir)
    md_dir.mkdir(parents=True, exist_ok=True)

    download_response = requests.get(zip_url)
    if download_response.status_code != 200:
        raise requests.RequestException(f"下载 zip 文件失败: {download_response.text}")

    # 设置压缩包下载路径和解压路径
    zip_path = md_dir / f"{file_title}.zip"
    extract_dir = md_dir / file_title

    zip_path.write_bytes(download_response.content)
    if extract_dir.is_dir():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(zip_path, extract_dir)

    # 根据 MinerU 的约定, 解压后的 full.md 文件即为最终的 Markdown 文件
    full_md = extract_dir / "full.md"
    if not full_md.is_file():
        raise RuntimeError("zip 文件解压后, 没有找到 full.md 文件")

    # 重命名 full.md 为 <file_title>.md
    md_path = full_md.rename(full_md.with_name(f"{file_title}.md"))
    logger.debug(f"下载并解压成功, md 路径: {md_path}")

    return md_path


@trace_node(desc="PDF 转 Markdown")
def node_pdf_to_md(state: ImportNodeState) -> ImportNodeState:
    """
    串联三步
    1. 校验 PDF
    2. MinerU 转换
    3.下载解压
    """

    # 1. 校验 PDF 并准备环境
    pdf_path, page_cnt, file_title = step_1_validate_and_setup(state)

    # 2. MinerU 转换
    zip_url = step_2_upload_and_poll(pdf_path, page_cnt)

    # 3. 下载解压
    md_path = step_3_download_and_unzip(zip_url, file_title)

    state["markdown_file_path"] = str(md_path)

    return state


if __name__ == "__main__":
    from rich import print as rprint
    from processor.import_processor.state import load_state, save_state
    from utils.path_utils import PROJECT_ROOT

    prev_state = load_state(str(PROJECT_ROOT / "output/tmp/import_01_entry.json"))
    next_state = node_pdf_to_md(prev_state)
    rprint(next_state)

    new_state_json = str(PROJECT_ROOT / "output/tmp/import_02_pdf_to_md.json")

    save_state(next_state, new_state_json)
    logger.info(f"PDF to Markdown 处理完成")
    logger.info(f"状态保存路径: {new_state_json}")
    logger.info(f"文件输出路径: {next_state['markdown_file_path']}")
