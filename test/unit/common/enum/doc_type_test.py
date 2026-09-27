"""单元测试: src/common/enum/doc_type.py

被测对象:
    DocType.from_filename     按后缀识别文档类型

TODO: 补充用例
    - "a.pdf" -> PDF, "b.MD" / "c.markdown" -> MARKDOWN (大小写不敏感)
    - 未知后缀 ("d.txt" / "e.docx") 回退 DocType.UNKNOWN
    - 无后缀或空字符串不抛异常, 返回 UNKNOWN
    - DocType 为 StrEnum, 可直接与字符串比较 (供 LangGraph 状态序列化)
"""
