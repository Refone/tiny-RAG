from utils.logging_utils import logger
from common.config.env_config import ENV_CONFIG
from pymilvus import DataType, MilvusClient


class RagMilvusClient(MilvusClient):
    def __init__(self):
        super().__init__(uri=ENV_CONFIG.milvus.endpoint)

    def prepare_item_name_collection(self):
        # 这里可以添加创建 item_name collection 的逻辑
        collection_name = ENV_CONFIG.milvus.collection_item_name

        # 如果 collection 已经存在，则直接返回
        has_collection = self.has_collection(collection_name)
        if has_collection:
            logger.info(f"Milvus collection '{collection_name}' 已存在")
            return

        # 如果 collection 不存在，则创建
        # 创建 schema
        # https://milvus.io/docs/schema.md#Create-Schema
        schema = self.create_schema(auto_id=True)
        schema.add_field(
            field_name="id", datatype=DataType.INT64, is_primary=True
        ).add_field(
            field_name="file_title", datatype=DataType.VARCHAR, max_length=0xFFFF
        ).add_field(
            field_name="item_name", datatype=DataType.VARCHAR, max_length=0xFFFF
        ).add_field(
            field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=1024
        ).add_field(
            field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR
        )

        # 创建索引参数 0.主键索引(auto) 1. 稠密向量索引 2. 稀疏向量索引
        index_params = self.prepare_index_params()

        # =========================
        # 稠密向量索引：dense_vector
        # =========================
        index_params.add_index(
            field_name="dense_vector",  # 与 schema 中的字段一致, 需要建索引的字段
            index_name="dense_vector_index",  # 自定义索引名称
            metric_type="COSINE",  # 距离度量方式，COSINE 表示余弦相似度
            index_type="HNSW",  # 索引算法类型，HNSW 分层导航小世界
            params={  # HNSW 算法专属参数
                "M": 64,  # 每个节点的最大出边数，越大召回越高、内存越大、构建越慢
                "efConstruction": 100,  # 构建索引时的候选队列大小，越大索引质量越高、构建越慢
            },
        )

        # 稀疏字段
        index_params.add_index(
            field_name="sparse_vector",  # 与 schema 中的字段一致, 需要建索引的字段
            index_name="sparse_vector_index",  # 自定义索引名称
            metric_type="IP",  # 距离度量方式，IP 表示内积
            index_type="SPARSE_INVERTED_INDEX",  # 索引算法类型，稀疏向量使用倒排索引
            params={
                "inverted_index_algo": "DAAT_MAXSCORE"
            },  # 倒排索引算法专用参数，动态剪枝，加速稀疏向量的 top-k 检索
        )

        # 创建 collection
        self.create_collection(
            collection_name=collection_name, schema=schema, index_params=index_params
        )

    def prepare_chunks_collection(self):
        # 这里可以添加创建 chunks collection 的逻辑
        collection_name = ENV_CONFIG.milvus.collection_chunks

        # 如果 collection 已经存在，则直接返回
        has_collection = self.has_collection(collection_name)
        if has_collection:
            logger.info(f"Milvus collection '{collection_name}' 已存在")
            return

        # 如果 collection 不存在，则创建
        # 创建 schema
        schema = self.create_schema(auto_id=True)
        schema.add_field(
            field_name="id", datatype=DataType.INT64, is_primary=True
        ).add_field(
            field_name="file_title", datatype=DataType.VARCHAR, max_length=0xFFFF
        ).add_field(
            field_name="item_name", datatype=DataType.VARCHAR, max_length=0xFFFF
        ).add_field(
            field_name="chunk_content", datatype=DataType.VARCHAR, max_length=0xFFFF
        ).add_field(
            field_name="dense_vector", datatype=DataType.FLOAT_VECTOR, dim=1024
        ).add_field(
            field_name="sparse_vector", datatype=DataType.SPARSE_FLOAT_VECTOR
        )

        # 创建索引参数
        index_params = self.prepare_index_params()

        # 稠密向量索引：dense_vector
        index_params.add_index(
            field_name="dense_vector",
            index_name="dense_vector_index",
            metric_type="COSINE",
            index_type="HNSW",
            params={
                "M": 64,
                "efConstruction": 100,
            },
        )

        # 稀疏字段
        index_params.add_index(
            field_name="sparse_vector",
            index_name="sparse_vector_index",
            metric_type="IP",
            index_type="SPARSE_INVERTED_INDEX",
            params={"inverted_index_algo": "DAAT_MAXSCORE"},
        )

        # 创建 collection
        self.create_collection(
            collection_name=collection_name, schema=schema, index_params=index_params
        )


if __name__ == "__main__":
    milvus_client = RagMilvusClient()
    milvus_client.prepare_item_name_collection()
    milvus_client.prepare_chunks_collection()
