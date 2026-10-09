"""单元测试: src/processor/import_processor/nodes/node_chunks_vect.py

被测对象:
    step_2_vect_chunks         切片向量化 (返回 content/dense/sparse)
    step_3_chunk_upsert_milvus 将向量化切片写入 Milvus
    node_chunks_vect           切片向量化节点 (读 chunks.json -> 入库)

说明:
    EMBEDDING / MILVUS_CLIENT 一律用假实现替换, 不触网也不连库。
    假实现的 dense_vector 取「文本长度」, 便于断言文本与向量按下标一一对应。
"""

from __future__ import annotations

import importlib
import json
import threading
import time
from pathlib import Path

import pytest

from processor.import_processor.nodes.node_chunks_vect import (
    node_chunks_vect,
    step_2_vect_chunks,
    step_3_chunk_upsert_milvus,
)
from processor.import_processor.state import create_state
from utils.markdown_splitter import Chunk

# 注意: 不能用 `from processor.import_processor.nodes import node_chunks_vect as mod` ——
# 包 __init__ 里 `from .node_chunks_vect import node_chunks_vect` 会用同名函数覆盖子模块属性,
# 取到的会是函数而不是模块, 导致 monkeypatch 无法替换模块内的 EMBEDDING / MILVUS_CLIENT。
mod = importlib.import_module("processor.import_processor.nodes.node_chunks_vect")

TASK_ID = "node-chunks-vect-unit-test"


# --------------------------------------------------------------------------- #
# 假实现: 记录调用, 让向量可反查文本
# --------------------------------------------------------------------------- #
class FakeEmbedding:
    """假嵌入模型: dense 用文本长度, sparse 用 {长度: 1.0}, 便于校验配对关系。"""

    def __init__(self, drop_last: bool = False, fail_on_batch: int | None = None):
        self.calls: list[list[str]] = []
        self.__drop_last = drop_last
        self.__fail_on_batch = fail_on_batch

    def embed(self, texts: list[str]) -> list[dict]:
        self.calls.append(list(texts))

        if self.__fail_on_batch is not None and len(self.calls) == self.__fail_on_batch:
            raise RuntimeError("偶发的嵌入服务不可用")

        vecs = [
            {"dense": [float(len(text))] * 2, "sparse": {len(text): 1.0}}
            for text in texts
        ]
        return vecs[:-1] if self.__drop_last else vecs


class FakeMilvus:
    """假 Milvus 客户端: 记录 delete / insert 调用。"""

    def __init__(self, insert_count_delta: int = 0):
        self.deleted: list[dict] = []
        self.insert_calls: list[list[dict]] = []
        self.__delta = insert_count_delta

    def delete(self, collection_name: str, filter: str) -> dict:
        self.deleted.append({"collection_name": collection_name, "filter": filter})
        return {"delete_count": 0}

    def insert(self, collection_name: str, data: list[dict]) -> dict:
        rows = [dict(row) for row in data]
        self.insert_calls.append(rows)
        return {
            "insert_count": len(rows) - self.__delta,
            "ids": list(range(len(rows))),
        }

    @property
    def inserted(self) -> list[dict]:
        """所有批次写入的行, 按写入顺序摊平。"""
        return [row for call in self.insert_calls for row in call]


class ConcurrencyProbeEmbedding(FakeEmbedding):
    """带延迟、可观测并发数的假嵌入: 用于验证嵌入请求确实并发而非串行。"""

    def __init__(self, delay: float = 0.02):
        super().__init__()
        self.delay = delay
        self.max_active = 0
        self._active = 0
        self._lock = threading.Lock()

    def embed(self, texts: list[str]) -> list[dict]:
        with self._lock:
            self._active += 1
            self.max_active = max(self.max_active, self._active)
        try:
            time.sleep(self.delay)
            return super().embed(texts)
        finally:
            with self._lock:
                self._active -= 1


def _chunk(content: str, title_stack: list[str] | None = None) -> Chunk:
    stack = title_stack or []
    return Chunk(content=content, level=len(stack), title_stack=stack)


def _vect_and_upsert(file_title: str, item_name: str, chunks: list[Chunk]) -> int:
    """模拟 node 的编排: 先向量化再写入, 便于复用原有用例。"""
    embedded = step_2_vect_chunks(chunks)
    return step_3_chunk_upsert_milvus(file_title, item_name, embedded)


@pytest.fixture()
def fakes(monkeypatch: pytest.MonkeyPatch):
    """替换模块内的 EMBEDDING / MILVUS_CLIENT, 返回 (embedding, milvus)。"""
    embedding, milvus = FakeEmbedding(), FakeMilvus()
    monkeypatch.setattr(mod, "EMBEDDING", embedding)
    monkeypatch.setattr(mod, "MILVUS_CLIENT", milvus)
    return embedding, milvus


# --------------------------------------------------------------------------- #
# 正常写入
# --------------------------------------------------------------------------- #
def test_writes_every_chunk_and_returns_count(fakes):
    embedding, milvus = fakes
    chunks = [
        _chunk("正文 A"),
        _chunk("正文 B", ["安全手册"]),
        _chunk("正文 C", ["安全手册", "规格"]),
    ]

    written = _vect_and_upsert("万用表", "万用表RS-12", chunks)

    assert written == 3
    assert len(milvus.inserted) == 3
    assert [row["chunk_content"] for row in milvus.inserted] == [
        "正文 A",
        "# 安全手册\n正文 B",
        "# 安全手册\n## 规格\n正文 C",
    ]
    for row in milvus.inserted:
        assert row["file_title"] == "万用表"
        assert row["item_name"] == "万用表RS-12"
        assert "id" not in row  # 主键由 Milvus 自增


def test_content_and_vector_come_from_the_same_embedded_text(fakes):
    """入库文本必须就是参与向量化的文本, 且向量与其一一对应 (不错位)。"""
    embedding, milvus = fakes
    chunks = [_chunk("短"), _chunk("长一点的内容", ["标题"])]

    _vect_and_upsert("万用表", "万用表RS-12", chunks)

    embedded_texts = [text for call in embedding.calls for text in call]
    assert embedded_texts == [row["chunk_content"] for row in milvus.inserted]

    for row in milvus.inserted:
        expected_len = float(len(row["chunk_content"]))
        assert row["dense_vector"] == [expected_len, expected_len]
        assert row["sparse_vector"] == {len(row["chunk_content"]): 1.0}


def test_step_2_returns_embedded_dicts_in_order(fakes):
    """step_2 返回 list[dict], 每个元素含 content/dense/sparse 且与切片同序。"""
    chunks = [_chunk("短"), _chunk("长一点的内容", ["标题"])]

    embedded = step_2_vect_chunks(chunks)

    assert [e["content"] for e in embedded] == ["短", "# 标题\n长一点的内容"]
    for e in embedded:
        assert set(e) == {"content", "dense", "sparse"}
        assert e["dense"] == [float(len(e["content"]))] * 2
        assert e["sparse"] == {len(e["content"]): 1.0}


def test_batches_embedding_by_ten_and_covers_all_chunks(fakes):
    embedding, milvus = fakes
    chunks = [_chunk(f"第 {i} 段") for i in range(21)]

    written = _vect_and_upsert("文档", "主体", chunks)

    # 并发下各批次的完成顺序不定, 只校验批次大小集合与总量
    assert sorted(len(call) for call in embedding.calls) == [1, 10, 10]
    assert written == 21
    assert len(milvus.inserted) == 21


def test_embedding_requests_run_concurrently_and_keep_order(monkeypatch):
    """向量化应并发请求嵌入模型, 且结果仍按下标顺序入库、不错位。"""
    probe = ConcurrencyProbeEmbedding(delay=0.02)
    milvus = FakeMilvus()
    monkeypatch.setattr(mod, "EMBEDDING", probe)
    monkeypatch.setattr(mod, "MILVUS_CLIENT", milvus)

    chunks = [_chunk(f"第 {i} 段") for i in range(30)]  # 30 段 -> 3 批

    written = _vect_and_upsert("文档", "主体", chunks)

    assert probe.max_active > 1  # 确实存在并发请求
    assert written == 30
    # 并发完成顺序即使打乱, 入库顺序仍与切片下标一致
    assert [row["chunk_content"] for row in milvus.inserted] == [
        f"第 {i} 段" for i in range(30)
    ]


def test_deletes_old_rows_by_file_title_before_writing(fakes):
    _, milvus = fakes

    _vect_and_upsert("万用表", "万用表RS-12", [_chunk("正文")])

    assert milvus.deleted == [
        {
            "collection_name": mod.ENV_CONFIG.milvus.collection_chunks,
            "filter": "file_title == '万用表'",
        }
    ]
    assert len(milvus.inserted) == 1


# --------------------------------------------------------------------------- #
# 边界与异常
# --------------------------------------------------------------------------- #
def test_empty_chunks_skips_embedding_and_milvus(fakes):
    embedding, milvus = fakes

    written = _vect_and_upsert("万用表", "万用表RS-12", [])

    assert written == 0
    assert embedding.calls == []
    assert milvus.deleted == []  # 没有新数据可写, 不应删掉库里已有的旧数据
    assert milvus.insert_calls == []


def test_embedding_count_mismatch_raises_before_delete(monkeypatch: pytest.MonkeyPatch):
    """接口少返回向量时必须失败, 而不是错位入库。"""
    milvus = FakeMilvus()
    monkeypatch.setattr(mod, "EMBEDDING", FakeEmbedding(drop_last=True))
    monkeypatch.setattr(mod, "MILVUS_CLIENT", milvus)

    with pytest.raises(ValueError, match="向量化结果数量与切片数量不一致"):
        _vect_and_upsert("万用表", "万用表RS-12", [_chunk("正文")])

    assert milvus.deleted == []
    assert milvus.insert_calls == []


def test_embedding_failure_keeps_existing_rows(monkeypatch: pytest.MonkeyPatch):
    """第二批向量化失败时, 库里已有的旧数据不能被提前删除。"""
    milvus = FakeMilvus()
    monkeypatch.setattr(mod, "EMBEDDING", FakeEmbedding(fail_on_batch=2))
    monkeypatch.setattr(mod, "MILVUS_CLIENT", milvus)

    chunks = [_chunk(f"第 {i} 段") for i in range(11)]

    with pytest.raises(RuntimeError, match="嵌入服务不可用"):
        _vect_and_upsert("万用表", "万用表RS-12", chunks)

    assert milvus.deleted == []
    assert milvus.insert_calls == []


def test_insert_count_mismatch_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mod, "EMBEDDING", FakeEmbedding())
    monkeypatch.setattr(mod, "MILVUS_CLIENT", FakeMilvus(insert_count_delta=1))

    with pytest.raises(RuntimeError, match="写入 Milvus 条数不一致"):
        _vect_and_upsert("万用表", "万用表RS-12", [_chunk("正文")])


# --------------------------------------------------------------------------- #
# 节点编排: 读 chunks.json -> 向量化入库
# --------------------------------------------------------------------------- #
def test_node_reads_chunks_file_and_upserts(tmp_path: Path, fakes):
    embedding, milvus = fakes
    chunks_path = tmp_path / "doc_chunks.json"
    chunks_path.write_text(
        json.dumps(
            [
                {"content": "正文 A", "level": 0, "title_stack": []},
                {"content": "正文 B", "level": 1, "title_stack": ["安全手册"]},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    state = create_state(
        task_id=TASK_ID,
        file_title="万用表",
        item_name="万用表RS-12",
        chunks_json_path=str(chunks_path),
    )

    result = node_chunks_vect(state)

    assert result is state  # 原样透传
    assert embedding.calls == [["正文 A", "# 安全手册\n正文 B"]]
    assert [row["chunk_content"] for row in milvus.inserted] == [
        "正文 A",
        "# 安全手册\n正文 B",
    ]


def test_node_requires_item_name(tmp_path: Path, fakes):
    """item_name 缺失时应在入口校验阶段失败, 不触碰 Milvus。"""
    _, milvus = fakes
    chunks_path = tmp_path / "doc_chunks.json"
    chunks_path.write_text("[]", encoding="utf-8")
    state = create_state(
        task_id=TASK_ID,
        file_title="万用表",
        item_name="",
        chunks_json_path=str(chunks_path),
    )

    with pytest.raises(ValueError, match="item_name 缺失"):
        node_chunks_vect(state)

    assert milvus.deleted == []
    assert milvus.insert_calls == []
