# Shop Assistant Agent

## 基本架构

```shell
docker  # docker 启动文件
docs    # 项目文档与笔记
src     # 主要源码
├── api     # FastAPI 相关源码
├── common  # 公共逻辑
│   ├── config  # 各种配置类
│   ├── enum    # 枚举定义
│   └── prompt  # 提示词模板
├── processor   # 核心 LangGraph 处理逻辑
│   ├── import_processor    # 导入流程: 文档导入-切分-向量化-落库
│   └── query_processor     # 查询流程: query-向量化-三路召回-生成答案
├── utils   # 工具逻辑
└── web     # 最终 Web 呈现
test    # pytest 测试目录
├── unit            # 单元测试, 与 src 目录一一镜像 (默认运行)
├── smoke           # 冒烟测试, 真实 apikey / 网络请求 (默认跳过)
├── integration     # 集成测试, 模块耦合 (默认跳过)
├── experimental    # 试验性脚本, 仅供参考
└── test-data       # 测试样例文件
```

## 测试

统一使用标准 pytest (不再依赖各文件 `__main__` 自测), 配置集中在
`pyproject.toml` 的 `[tool.pytest.ini_options]`。

**镜像约定**: `test/unit` 与 `src` 逐层对应, 测试文件命名为 `<模块名>_test.py`。
例如 `src/utils/path_utils.py` → `test/unit/utils/path_utils_test.py`。
`pythonpath = ["src"]` 让测试里可以直接 `import utils.xxx`, 无需安装包。

```shell
uv run pytest                      # 只跑单元测试 (smoke / integration 自动跳过)
uv run pytest --run-smoke          # 连同冒烟测试一起跑 (真实网络)
uv run pytest --run-integration    # 连同集成测试一起跑
uv run pytest test/unit/utils      # 只跑某个目录
uv run pytest -k doc_type          # 只跑名字匹配的用例
```

测试分三档 marker, 由 `--run-*` 开关控制:

| marker | 含义 | 默认 | 开启方式 |
| --- | --- | --- | --- |
| `unit` | 单元测试, mock 所有外部依赖 | ✅ 运行 | (无需开关) |
| `smoke` | 冒烟测试, 真实 apikey / 网络请求 | ⏭ 跳过 | `--run-smoke` |
| `integration` | 模块耦合集成测试 (Milvus / MinIO / LLM) | ⏭ 跳过 | `--run-integration` |

冒烟测试想看节点过程日志, 加 `-s -v` 关闭输出捕获:

```shell
uv run pytest test/smoke -s -v --run-smoke
```
