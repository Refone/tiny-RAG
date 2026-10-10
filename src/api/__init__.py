"""FastAPI 框架层: HTTP 入口、路由、DTO、依赖注入。

本层只做 HTTP 编解码与参数校验, 不包含业务逻辑。
依赖方向 (单向): api -> service -> processor -> common/utils。
"""

__version__ = "0.1.0"
