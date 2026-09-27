"""单元测试: src/processor/import_processor/nodes/node_entry.py

被测对象:
    node_entry    入口节点: 文件存在性校验 + 类型识别 + 状态补全

TODO: 补充用例
    - 文件不存在时原状态返回, 不抛异常
    - .txt 等不支持类型 -> doc_type 为 DocType.UNKNOWN, 不设置 markdown_file_path
    - .md 文件 -> doc_type=MARKDOWN, 且 markdown_file_path 指向原文件
    - .pdf 文件 -> doc_type=PDF, 且不设置 markdown_file_path
    - 用例直接复用 test/test-data 下的样例 (用 test_data_dir / sample_* fixture)
"""
