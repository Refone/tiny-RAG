"""单元测试: src/processor/import_processor/nodes/node_pdf_to_md.py

被测对象:
    step_1_validate_and_setup    PDF 文件校验与工作目录准备
    step_2_upload_and_poll       上传 MinerU 并轮询转换结果 (外部 HTTP)
    step_3_download_and_unzip    下载并解压结果包
    node_pdf_to_md               节点入口

说明:
    - 所有外部调用 (requests / time.sleep / from_project_root) 一律 mock, 不打真实网络。
    - 需要真实 MinerU API Key 的用例请放 test/smoke, 并加 @pytest.mark.smoke。
"""

from __future__ import annotations

import importlib
import io
import zipfile
from pathlib import Path

import pytest
import requests

# 注意: 不能用 `import ...nodes.node_pdf_to_md as ...`, 包 __init__ 把同名函数
# 重导出了, 会拿到函数而非模块; 用 importlib 直接从 sys.modules 取模块对象。
node_pdf_to_md = importlib.import_module("processor.import_processor.nodes.node_pdf_to_md")
from processor.import_processor.state import create_state


class FakeResponse:
    """requests 响应替身。"""

    def __init__(self, status_code: int = 200, json_data=None, text: str = "", content: bytes = b""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text
        self.content = content

    def json(self):
        return self._json


class FakeSession:
    """requests.Session 替身: 记录 put 调用并返回指定响应。"""

    def __init__(self, put_response: FakeResponse | None = None):
        self.put_response = put_response or FakeResponse()
        self.put_calls: list[dict] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def put(self, url, data=None):
        self.put_calls.append({"url": url, "data": data})
        return self.put_response


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _make_pdf(tmp_path: Path, name: str = "doc.pdf") -> Path:
    """写入一个仅带 PDF 魔数的临时文件 (足够通过 step_1 的头部校验)。"""
    path = tmp_path / name
    path.write_bytes(b"%PDF-1.4\nfake pdf body")
    return path


def _configure_mineru(monkeypatch, *, base_url: str = "https://mineru.example", api_key: str = "secret"):
    monkeypatch.setattr(node_pdf_to_md.ENV_CONFIG.mineru, "base_url", base_url)
    monkeypatch.setattr(node_pdf_to_md.ENV_CONFIG.mineru, "api_key", api_key)


def _apply_response(batch_id: str = "batch-1", upload_url: str = "https://upload.example/presign") -> FakeResponse:
    return FakeResponse(
        json_data={"code": 0, "data": {"file_urls": [upload_url], "batch_id": batch_id}}
    )


def _poll_response(state: str, zip_url: str | None = None) -> FakeResponse:
    item = {"state": state}
    if zip_url is not None:
        item["full_zip_url"] = zip_url
    return FakeResponse(json_data={"code": 0, "msg": "ok", "data": {"extract_result": [item]}})


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    """在内存中构造 zip 包, 供 step_3 的 mock 响应使用。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _patch_step2_network(monkeypatch, *, apply_response=None, put_response=None, get_side_effect=None):
    """统一 mock step_2 涉及的三个 HTTP 入口。"""
    monkeypatch.setattr(
        node_pdf_to_md.requests, "post", lambda *a, **k: apply_response or _apply_response()
    )
    monkeypatch.setattr(node_pdf_to_md.requests, "Session", lambda: FakeSession(put_response))
    if get_side_effect is not None:
        calls = iter(get_side_effect)
        monkeypatch.setattr(node_pdf_to_md.requests, "get", lambda *a, **k: next(calls))


# --------------------------------------------------------------------------- #
# step_1: 文件校验
# --------------------------------------------------------------------------- #
def test_step1_empty_path_raises():
    state = create_state(task_id="t", origin_file_path="")
    with pytest.raises(ValueError, match="origin_file_path 为空"):
        node_pdf_to_md.step_1_validate_and_setup(state)


def test_step1_missing_file_raises(tmp_path: Path):
    state = create_state(task_id="t", origin_file_path=str(tmp_path / "not-exist.pdf"))
    with pytest.raises(ValueError, match="文件不存在"):
        node_pdf_to_md.step_1_validate_and_setup(state)


def test_step1_non_pdf_raises(tmp_path: Path):
    path = tmp_path / "note.txt"
    path.write_text("plain text", encoding="utf-8")
    state = create_state(task_id="t", origin_file_path=str(path))
    with pytest.raises(ValueError, match="不是 PDF 格式"):
        node_pdf_to_md.step_1_validate_and_setup(state)


def test_step1_valid_pdf_sets_file_title(tmp_path: Path):
    path = _make_pdf(tmp_path, name="第一章-初识智能体.pdf")
    state = create_state(task_id="t", origin_file_path=str(path))

    result = node_pdf_to_md.step_1_validate_and_setup(state)

    assert result == path
    assert state["file_title"] == "第一章-初识智能体"


# --------------------------------------------------------------------------- #
# step_2: 上传 + 轮询
# --------------------------------------------------------------------------- #
def test_step2_missing_config_raises(monkeypatch, tmp_path: Path):
    _configure_mineru(monkeypatch, api_key="")
    with pytest.raises(ValueError, match="MinerU 配置错误"):
        node_pdf_to_md.step_2_upload_and_poll(_make_pdf(tmp_path))


def test_step2_apply_http_error(monkeypatch, tmp_path: Path):
    _configure_mineru(monkeypatch)
    _patch_step2_network(monkeypatch, apply_response=FakeResponse(status_code=500, text="boom"))
    with pytest.raises(requests.HTTPError, match="上传文件失败"):
        node_pdf_to_md.step_2_upload_and_poll(_make_pdf(tmp_path))


def test_step2_apply_business_error(monkeypatch, tmp_path: Path):
    _configure_mineru(monkeypatch)
    _patch_step2_network(
        monkeypatch,
        apply_response=FakeResponse(json_data={"code": 1, "msg": "quota exceeded"}),
    )
    with pytest.raises(requests.RequestException, match="业务逻辑失败"):
        node_pdf_to_md.step_2_upload_and_poll(_make_pdf(tmp_path))


def test_step2_apply_missing_upload_info(monkeypatch, tmp_path: Path):
    _configure_mineru(monkeypatch)
    _patch_step2_network(
        monkeypatch,
        apply_response=FakeResponse(json_data={"code": 0, "msg": "无上传地址", "data": {"file_urls": [], "batch_id": ""}}),
    )
    with pytest.raises(requests.RequestException, match="申请上传地址失败"):
        node_pdf_to_md.step_2_upload_and_poll(_make_pdf(tmp_path))


def test_step2_put_upload_error(monkeypatch, tmp_path: Path):
    _configure_mineru(monkeypatch)
    _patch_step2_network(monkeypatch, put_response=FakeResponse(status_code=403, text="denied"))
    with pytest.raises(requests.RequestException, match="上传文件失败"):
        node_pdf_to_md.step_2_upload_and_poll(_make_pdf(tmp_path))


def test_step2_poll_success(monkeypatch, tmp_path: Path):
    _configure_mineru(monkeypatch)
    pdf_path = _make_pdf(tmp_path)
    session = FakeSession()
    poll_responses = iter(
        [_poll_response("processing"), _poll_response("done", "https://cdn.example/result.zip")]
    )

    monkeypatch.setattr(node_pdf_to_md.requests, "post", lambda *a, **k: _apply_response())
    monkeypatch.setattr(node_pdf_to_md.requests, "Session", lambda: session)
    monkeypatch.setattr(node_pdf_to_md.requests, "get", lambda *a, **k: next(poll_responses))
    monkeypatch.setattr(node_pdf_to_md.time, "sleep", lambda _: None)

    result = node_pdf_to_md.step_2_upload_and_poll(pdf_path)

    assert result == "https://cdn.example/result.zip"
    # 上传环节确以 PDF 原始字节为 body
    assert session.put_calls[0]["data"] == pdf_path.read_bytes()


def test_step2_poll_failed_state(monkeypatch, tmp_path: Path):
    _configure_mineru(monkeypatch)
    _patch_step2_network(
        monkeypatch,
        get_side_effect=[_poll_response("failed")],
    )
    monkeypatch.setattr(node_pdf_to_md.time, "sleep", lambda _: None)
    with pytest.raises(requests.RequestException, match="MinerU 解析失败"):
        node_pdf_to_md.step_2_upload_and_poll(_make_pdf(tmp_path))


def test_step2_poll_timeout(monkeypatch, tmp_path: Path):
    _configure_mineru(monkeypatch)
    _patch_step2_network(
        monkeypatch,
        get_side_effect=[_poll_response("processing")],
    )
    monkeypatch.setattr(node_pdf_to_md.time, "sleep", lambda _: None)
    # 将超时阈值设为负数, 第一次进入循环即超时, 不依赖真实时钟
    monkeypatch.setattr(node_pdf_to_md, "_POLL_TIMEOUT_SECONDS", -1)

    with pytest.raises(requests.Timeout, match="转换超时"):
        node_pdf_to_md.step_2_upload_and_poll(_make_pdf(tmp_path))


# --------------------------------------------------------------------------- #
# step_3: 下载 + 解压
# --------------------------------------------------------------------------- #
def test_step3_download_http_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(node_pdf_to_md, "from_project_root", lambda rel: tmp_path)
    monkeypatch.setattr(
        node_pdf_to_md.requests, "get", lambda *a, **k: FakeResponse(status_code=500, text="boom")
    )
    state = create_state(task_id="t", file_title="report")

    with pytest.raises(requests.RequestException, match="下载 zip 文件失败"):
        node_pdf_to_md.step_3_download_and_unzip("https://cdn.example/result.zip", state)


def test_step3_missing_full_md(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(node_pdf_to_md, "from_project_root", lambda rel: tmp_path)
    monkeypatch.setattr(
        node_pdf_to_md.requests,
        "get",
        lambda *a, **k: FakeResponse(content=_zip_bytes({"other.txt": b"x"})),
    )
    state = create_state(task_id="t", file_title="report")

    with pytest.raises(RuntimeError, match="没有找到 full.md"):
        node_pdf_to_md.step_3_download_and_unzip("https://cdn.example/result.zip", state)


def test_step3_success(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(node_pdf_to_md, "from_project_root", lambda rel: tmp_path)
    monkeypatch.setattr(
        node_pdf_to_md.requests,
        "get",
        lambda *a, **k: FakeResponse(content=_zip_bytes({"full.md": "# 正文".encode("utf-8")})),
    )
    state = create_state(task_id="t", file_title="report")

    result = node_pdf_to_md.step_3_download_and_unzip("https://cdn.example/result.zip", state)

    expected = tmp_path / "report" / "report.md"
    assert result == expected
    assert expected.is_file()
    assert expected.read_text(encoding="utf-8") == "# 正文"
    # full.md 已被重命名, 不再残留
    assert not (tmp_path / "report" / "full.md").exists()


# --------------------------------------------------------------------------- #
# node_pdf_to_md: 串联
# --------------------------------------------------------------------------- #
def test_node_pdf_to_md_orchestrates_steps(monkeypatch, tmp_path: Path):
    md_path = tmp_path / "out" / "report.md"
    monkeypatch.setattr(node_pdf_to_md, "step_1_validate_and_setup", lambda state: _make_pdf(tmp_path))
    monkeypatch.setattr(
        node_pdf_to_md, "step_2_upload_and_poll", lambda pdf: "https://cdn.example/result.zip"
    )
    monkeypatch.setattr(node_pdf_to_md, "step_3_download_and_unzip", lambda url, state: md_path)

    state = create_state(task_id="t", origin_file_path=str(tmp_path / "in.pdf"))
    result = node_pdf_to_md.node_pdf_to_md(state)

    assert result is state
    assert result["markdown_file_path"] == str(md_path)
