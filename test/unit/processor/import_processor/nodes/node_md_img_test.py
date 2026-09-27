"""单元测试: src/processor/import_processor/nodes/node_md_img.py

被测对象:
    node_md_img    图片处理节点 (上传 MinIO + 替换 Markdown 图片链接)

当前状态: 尚未实现, 仅透传 state (见源码 TODO)。

TODO: 实现后补充用例
    - 扫描 Markdown 中的图片链接
    - 图片上传 MinIO 失败时的降级行为 (mock minio 客户端)
    - 成功时 markdown_file_path / md_content 中的链接被替换为 MinIO URL
    - 无图片的 Markdown 不产生副作用
"""
