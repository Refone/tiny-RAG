# Shop Assistant Agent

## 基本架构

```shell
docker  # docker 启动文件
notes   # 项目笔记
src     # 主要源码
├── api     # FastAPI 相关源码
├── common  # 公共逻辑
│   ├── config  # 各种配置类
│   ├── logging # 日志记录
│   └── prompt  # 提示词模板
├── processor   # 核心 LangGraph 处理逻辑
│   ├── import_processor    # 导入流程: 文档导入-切分-向量化-落库
│   └── query_processor     # 查询流程: query-向量化-三路召回-生成答案
├── test    # 集成测试 (单元测试在每个文件 __main__ 中)
├── utils   # 工具逻辑
└── web     # 最终 Web 呈现
```
