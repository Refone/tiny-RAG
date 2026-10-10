"""聊天服务: 预留。

等 query_processor 图落地后, 在此编排调用 (消息历史、检索、流式输出)。
当前返回纯数据 (dict), 由 api 层映射为响应 DTO, 保持 service -> api 不反向依赖。
"""


async def achat(message: str) -> str:
    """调用查询/对话图。当前 query_processor 尚未实现。"""
    raise NotImplementedError(
        "chat 端点尚未实现: query_processor 图还未落地, "
        "见 src/processor/query_processor/"
    )
