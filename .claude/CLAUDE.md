# CLAUDE.md

## 项目简介

RAG Agent，LangGraph 编排。导入链路已实现，查询链路待实现。

## 核心约束

- 代码修改需要通过单元测试和冒烟测试。
- 如果发现单元测试有缺陷，或阻碍项目演进，可上报。

## 常用命令

- 运行单元测试：`uv run pytest`（默认只跑 unit，smoke / integration 自动跳过）
- 运行冒烟测试：`uv run pytest test/smoke -s -v --run-smoke`（真实 apikey / 网络）
- 运行集成测试：`uv run pytest --run-integration`（需 Milvus/MinerU/LLM）
- 调试导入流程 (PDF)：直接运行 `dev/import_pdf.py`
- 安装依赖：`uv sync`

## 导入链路（7 节点）

1. `node_entry` ✅ — 文件识别 + 状态补全
2. `node_pdf_to_md` ✅ — MinerU 云端转换（依赖 `MINERU_API_KEY`）
3. `node_md_img` TODO — 图片上传 MinIO + 多模态描述
4. `node_document_split` TODO — 标题递归切分 + Metadata
5. `node_item_name_recognize` TODO — LLM 归纳主体
6. `node_bge_embedding` TODO — BGE-M3 稠密/稀疏向量
7. `node_upsert_milvus` TODO — 删旧 + 批量插入

**实现 TODO 节点时**：先更新 `state.py`，再写节点函数，最后在 `nodes/__init__.py` 导出。

## 项目结构（关键部分）

- `src/processor/import_processor/` — 导入链路核心
- `src/processor/query_processor/` — 查询链路（空）
- `src/utils/node_utils.py` — 节点装饰器
- `test/unit/` — 单元测试，与 src 镜像
- `test/smoke/` — 冒烟测试，真实外部服务（`--run-smoke` 开启）
- `dev/` — 实验性调试脚本（直接运行观察 src 逻辑，不受测试保护）

## 架构图

见 ![架构图](docs/architecture.png)

## 关于 Git

可以执行任何只读命令, 但是不要有任何改变状态的操作 (包括但不限于 `git add`、`git commit` 等)。
