"""业务编排层: 把 LangGraph 图包装成可供 API 层调用的服务。

依赖方向 (单向): api -> service -> processor -> common/utils。
本层负责组装图、管理会话/状态、流式输出, 不碰 HTTP 细节。
"""
