from dashscope import TextEmbedding
from common.config.env_config import ENV_CONFIG
from typing import Any
from common.model.rate_limiter import SlidingWindowRateLimiter


# https://www.qianwenai.com/models/text-embedding-v4
class QwenEmbedding:
    def __init__(self):
        self.model = ENV_CONFIG.embedding.model
        self.rpm = ENV_CONFIG.embedding.rpm
        self.dense_dimension = ENV_CONFIG.embedding.dense_dimension
        self.__api_key = ENV_CONFIG.qwen.api_key

        self.__limiter = SlidingWindowRateLimiter(self.rpm)

    def embed(self, texts: list[str]) -> list[dict[str, Any]]:
        """
        将文本列表嵌入为稠密和稀疏向量。

        Args:
            texts (list[str]): 文本列表

        Returns:
            list[dict[str, Any]]: 包含稠密和稀疏向量的字典列表。
            其中每个字典包含两个键：
                - "dense": 稠密向量列表
                - "sparse": 稀疏向量字典，键为索引，值为对应的浮点数
        """
        self.__limiter.acquire()  # 在调用嵌入接口前进行速率限制

        resp = TextEmbedding.call(
            model=self.model,
            api_key=self.__api_key,
            input=texts,
            output_type="dense&sparse",  # 同时返回稠密和稀疏向量
            text_type="document",  # 文档场景用 document，查询场景用 query
            dimension=self.dense_dimension,  # 稠密向量的维度（不影响稀疏向量）
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"TextEmbedding 调用失败: code={resp.status_code}, "
                f"message={getattr(resp, 'message', resp)}"
            )

        embeddings = resp["output"]["embeddings"]
        result: list[dict[str, Any]] = []
        for emb in embeddings:
            dense = emb["embedding"]
            sparse_obj = emb.get("sparse_embedding") or {}
            sparse = {int(item["index"]): float(item["value"]) for item in sparse_obj}
            result.append({"dense": dense, "sparse": sparse})

        return result


if __name__ == "__main__":
    from rich import print as rprint

    embedding = QwenEmbedding()
    result = embedding.embed(["Hello World", "Hello RAG", "你好, 朋友"])
    for i, r in enumerate(result):
        rprint(f"Text {i}:")
        rprint(f"  Dense: {r['dense'][0:5]}")
        rprint(f"  Sparse: {r['sparse']}")
