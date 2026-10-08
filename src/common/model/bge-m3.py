
from scipy.sparse import csr_matrix

from utils.path_utils import PROJECT_ROOT
from utils.logging_utils import logger
from common.config.env_config import ENV_CONFIG
from pymilvus.model.hybrid import BGEM3EmbeddingFunction

class _BGE_M3_LLM:
    def __init__(self):
        # 初始化 OpenAI Embeddings 实例
        local_bge_model_path = PROJECT_ROOT / ENV_CONFIG.embedding.model_local_path

        self.embeddings = BGEM3EmbeddingFunction(
            model_name=str(local_bge_model_path),
            device="cpu",
            use_fp16=False,
            return_dense=True,
            return_sparse=True,
            normalize_embeddings=True,
        )

    def get_embeddings(self, texts: list[str]) -> list[tuple[list[float], dict[int, float]]]:

        if not isinstance(texts, list) or \
            not all(isinstance(t, str) for t in texts) or \
            not len(texts) > 0:
            raise ValueError("参数 texts 必须是包含文本的非空列表")

        logger.debug(f"Getting embeddings for texts: {texts}")

        embeddings = self.embeddings.encode_documents(texts)
        """
        {
            'dense': [
                array([-0.03447856,  0.03034053, -0.02515052, ...,  0.03058447, -0.03408333,  0.00765713], shape=(1024,), dtype=float32),
                array([-0.01924711,  0.02181231, -0.04565993, ..., -0.01202198, 0.00392589,  0.01788769], shape=(1024,), dtype=float32),
                array([-0.03306571,  0.02509659, -0.04802828, ..., -0.00373621, -0.0140302 ,  0.01034628], shape=(1024,), dtype=float32)
            ],
            'sparse': <Compressed Sparse Row sparse array of dtype 'float64' with 11 stored elements and shape (3, 250002)>
        }
        """

        # bge-m3 词表大小为 25000, 稀疏向量的长度应为 25000
        # 这里把稀疏向量用 CSR 压缩为字典
        # CSR: ![](docs/CSR.md)
        """
        [[0, 0, 3, 0, 4],
         [0, 0, 0, 0, 0],
         [1, 0, 0, 0, 2]]

        data    = [3, 4, 1, 2]
        indices = [2, 4, 0, 4]
        indptr  = [0, 2, 2, 4]
        """

        sparse = embeddings["sparse"]
        sparse_dicts = []
        for i in range(len(texts)):
            indices = sparse.indices[sparse.indptr[i]:sparse.indptr[i+1]].tolist()
            data = sparse.data[sparse.indptr[i]:sparse.indptr[i+1]].tolist()
            sparse_dict = dict(zip(indices, data))
            sparse_dicts.append(sparse_dict)

        result = {
            "dense": [ emb.tolist() for emb in embeddings["dense"] ],
            "sparse": sparse_dicts,
        }

        return result

EMBEDDINGS = _BGE_M3_LLM()

if __name__ == "__main__":
    from rich import print as rprint

    result = EMBEDDINGS.get_embeddings(
                            [
                                "Hello, World",
                                "This is a test",
                                "this just a test",
                            ]
                        )
    print(len(result["dense"]), len(result["dense"][0]))
    rprint(result["sparse"])