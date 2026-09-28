# dev/ — 实验性调试脚本

本目录用于存放「实验性调试主流程」的脚本, 直接运行对应文件即可观察 `src` 中
代码逻辑的真实效果; 不纳入 pytest 收集范围, 也不受测试保护。

## 文件清单

| 文件 | 调试的流程 |
| --- | --- |
| `import_pdf.py` | 导入流程 (import_processor) 的 PDF 分支: 以 hak180 样例走 MinerU 转 Markdown, 直接运行后打印完成节点链与最终 state |
