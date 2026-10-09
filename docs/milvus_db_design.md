# Milvus 数据库设计

**文档级索引（kb_item_name）**

核心定位：作为检索的 “一级筛选器”，快速锁定目标文档范围，减少全库切片检索的性能损耗。

| 字段名        | 字段类型          | 核心作用                                                       |
| :------------ | :---------------- | :------------------------------------------------------------- |
| id            | Int64（自增主键） | 文档级唯一标识，用于数据管理与关联                             |
| file_title    | VarChar(65535)    | 原始文档名称，用于数据溯源与文档级管理                         |
| item_name     | VarChar(65535)    | 文档核心主体（如 “iPhone 17 Pro Max”），解决跨文档主体模糊问题 |
| dense_vector  | FloatVector(1024) | 主体名称的语义向量，支持模糊语义匹配                           |
| sparse_vector | SparseFloatVector | 主体名称的关键词向量，支持专业术语、实体的精确匹配             |

**切片级索引（kb_chunks）**

**核心定位**：检索的 “精准匹配层”，存储细粒度语义切片，直接为大模型提供上下文证据。

| 字段名        | 字段类型          | 核心作用                                               |
| :------------ | :---------------- | :----------------------------------------------------- |
| id            | Int64（自增主键） | 切片全局唯一标识，作为数据操作主键                     |
| file_title    | VarChar(65535)    | 关联原始文档名称，实现切片 - 文档溯源                  |
| item_name     | VarChar(65535)    | 关联文档级核心主体，解决切片主语缺失问题               |
| chunk_content | VarChar(65535)    | 切片文本内容（含标题层级），是向量编码的核心数据源     |
| dense_vector  | FloatVector(1024) | 切片语义向量，适配模糊语义检索，提升上下文匹配度       |
| sparse_vector | SparseFloatVector | 切片关键词向量，适配精确检索，提升术语匹配精度         |

> 字段以 `src/common/client/milvus_client.py` 的 `prepare_chunks_collection` 建表逻辑为准。
> 切片的标题层级目前由 `_format_chunk_content` 拼成 Markdown 标题行随 `chunk_content` 一并写入，
> 未单独建 `title` / `parent_title` / `part` 字段；若后续需要按标题路径过滤或加权，再扩展 schema。
