from pathlib import Path
import shutil
import time

import requests

from common.config.settings import config
from processor.import_processor.state import ImportNodeState
from utils.logging_utils import logger
from utils.node_utils import step_log, trace_node
from utils.path_utils import from_project_root

@step_log("校验 PDF 文件")
def step_1_validate_and_setup(state: ImportNodeState) -> Path:
    pdf_path = state.get("origin_file_path")

    if not pdf_path:
        raise ValueError(f"路径错误: {state["origin_file_path"]}")

    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.is_file():
        raise ValueError(f"文件不存在或不是一个文件: {pdf_path_obj}")

    with open(pdf_path_obj, "rb") as f:
        if f.read(5) != b"%PDF-":
            raise ValueError(f"文件不是 PDF 格式: {pdf_path_obj}")

    state["file_title"] = pdf_path_obj.stem

    logger.debug(f"PDF 校验通过: {str(pdf_path_obj)}")
    return pdf_path_obj

@step_log("上传PDF,轮询等待转换完成")
def step_2_upload_and_poll(pdf_path_obj: Path) -> str:
    if not config.mineru.base_url or not config.mineru.api_key:
        raise ValueError("MinerU 配置错误, 请检查 .env 是否正确配置 MINERU_ 相关参数")

    # 相关配置参考: https://mineru.net/apiManage/docs
    api_key = config.mineru.api_key
    url = f"{config.mineru.base_url}/file-urls/batch"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "files": [
            {"name": f"{pdf_path_obj.name}", "data_id":f"{pdf_path_obj.stem}"}
        ],
        "model_version": "vlm"
    }

    response = requests.post(url, headers=headers, json=data)

    http_status_code = response.status_code
    if http_status_code != 200:
        raise requests.HTTPError(f"MinerU 上传文件失败: {response.text}")

    response_data = response.json()
    if response_data["code"] != 0:
        raise requests.RequestException(f"HTTP请求成功, 但业务逻辑失败: {response_data['msg']}")

    file_upload_urls = response_data["data"]['file_urls']
    batch_id = response_data["data"]['batch_id']
    if not file_upload_urls or not batch_id:
        raise requests.RequestException(f"申请上传地址失败: {response_data['msg']}")

    # with open(from_project_root("output/request_url_response.json"), "w", encoding="utf-8") as f:
    #     json.dump(response_data, f)
    file_upload_url = file_upload_urls[0]
    logger.debug(f"申请上传地址成功: {batch_id=}, {file_upload_url=}")

    pdf_file_data = pdf_path_obj.read_bytes()
    # 获取 session 对象
    with requests.Session() as session:
        # 上传文件
        response = session.put(file_upload_url, data=pdf_file_data)
        # 检查响应状态码
        ## 不返回 body, 仅有状态码确认上传成功
        if response.status_code != 200:
            raise requests.RequestException(f"上传文件失败: {response.text}")

    url = f"{config.mineru.base_url}/extract-results/batch/{batch_id}"
    logger.debug(f"上传文件成功, 轮询 url: {url}")

    # 轮询获取转换结果
    timeout = 600 # 超过 10 min 钟没有转换完成, 就放弃, 设置依据: 官方说明: 1页pdf 0.5~1s
    interval_time = 3   # 每隔 3s 轮询一次
    start_time = time.time()
    while True:
        time.sleep(interval_time)

        if time.time() - start_time > timeout:
            raise requests.Timeout("转换超时")

        try:
            poll_response = requests.get(url, headers=headers)
        except Exception:
            logger.debug(f"请求异常, 3s 后重试")
            continue

        if poll_response.status_code != 200:
            logger.debug(f"请求失败, 3s 后重试")
            continue

        poll_response_data = poll_response.json()
        if poll_response_data["code"] != 0:
            raise requests.RequestException(f"MinerU 解析失败: {poll_response_data['msg']}")

        # with open(from_project_root("output/poll_response.json"), "w", encoding="utf-8") as f:
        #     json.dump(poll_response_data, f)

        extract_result = poll_response_data["data"]["extract_result"][0]
        extract_result_state = extract_result["state"]
        if extract_result_state == "done":
            extract_result_url = extract_result["full_zip_url"]
            if not extract_result_url:
                raise requests.RequestException(f"MinerU 解析完毕, zip 地址异常: {poll_response_data['msg']}")

            logger.debug(f"MinerU 解析完毕, zip 地址: {extract_result_url}")
            return extract_result_url
        elif extract_result_state == "failed":
            raise requests.RequestException(f"MinerU 解析失败: {poll_response_data['msg']}")
        else:
            # 还在解析中
            logger.debug(f"尚在解析, 3s 后重试")
            continue

@step_log("下载并解压")
def step_3_download_and_unzip(zip_url: str, state: ImportNodeState) -> Path:
    """
    下载并解压 zip 文件
    """
    md_folder_path_obj = from_project_root("output/markdown-folder")
    if not md_folder_path_obj.is_dir():
        md_folder_path_obj.mkdir(parents=True, exist_ok=True)

    response = requests.get(zip_url)
    if response.status_code != 200:
        raise requests.RequestException(f"下载 zip 文件失败: {response.text}")

    zip_path_obj = md_folder_path_obj / f"{state['file_title']}.zip"
    extract_path_obj = md_folder_path_obj / state["file_title"]

    zip_path_obj.write_bytes(response.content)
    if extract_path_obj.is_dir():
        shutil.rmtree(extract_path_obj)
    extract_path_obj.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(zip_path_obj, extract_path_obj)

    md_file_obj = extract_path_obj / "full.md"
    if not md_file_obj.is_file():
        raise RuntimeError("zip 文件解压后, 没有找到 full.md 文件")

    md_file_obj = md_file_obj.rename(md_file_obj.with_name(f"{state['file_title']}.md"))

    logger.debug(f"下载并解压成功, md 路径: {md_file_obj}")
    return md_file_obj



@trace_node(desc="PDF 转 Markdown")
def node_pdf_to_md(state: ImportNodeState) -> ImportNodeState:
    """
    PDF 转 Markdown 节点

    step 1: 校验路径、PDF文件头、提取文档标题
    step 2: 通过 MinerU 进行
            - 请求上传地址
            - 上传文件
            - 轮询获取转换结果
            获得 zip 的下载 url
    step 3: 下载 zip, 解压, 重命名, 更新 state 状态
    """
    # 1. 校验路径完整以及文件是否真实存在
    pdf_path_obj = step_1_validate_and_setup(state)

    zip_url = step_2_upload_and_poll(pdf_path_obj)

    md_path = step_3_download_and_unzip(zip_url, state)

    state["markdown_file_path"] = str(md_path)

    return state

if __name__ == "__main__":
    from processor.import_processor.state import create_state
    from rich import print as rprint

    start = create_state(
        task_id="UNIT-TEST:node_pdf_to_md",
        origin_file_path=from_project_root("test/test-data/hak180产品安全手册.pdf"),
    )
    end = node_pdf_to_md(start)

    rprint(end)