"""单元测试: src/processor/import_processor/nodes/node_pdf_to_md.py

被测对象:
    step_1_validate_and_setup    PDF 文件校验与工作目录准备
    step_2_upload_and_poll       上传 MinerU 并轮询转换结果 (外部 HTTP)
    step_3_download_and_unzip    下载并解压结果包
    node_pdf_to_md               节点入口

TODO: 补充用例 (所有外部调用一律 mock, 不打真实网络)
    - step_1: 非 PDF / 文件不存在时的行为, 以及输出目录创建
    - step_2: mock 响应覆盖「轮询中 -> 成功」与「失败 / 超时」分支
    - step_3: mock zip 下载到 tmp_path, 校验解压结果与返回值
    - node_pdf_to_md: 端到端串联三个 step (全部 mock), 校验状态字段更新

说明: 需要真实 MinerU API Key 的用例请放 test/integration, 并加 @pytest.mark.integration。
"""
