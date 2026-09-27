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
├── unit            # 单元测试, 与 src 目录一一镜像
├── integration     # 集成测试 (依赖 Milvus / MinerU / LLM, 默认跳过)
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
uv run pytest                      # 全部单元测试 (集成测试自动跳过)
uv run pytest --run-integration    # 连同集成测试一起跑
uv run pytest test/unit/utils      # 只跑某个目录
uv run pytest -k doc_type          # 只跑名字匹配的用例
```

集成测试需标注 `@pytest.mark.integration`, 默认跳过, 用 `--run-integration` 开启。
