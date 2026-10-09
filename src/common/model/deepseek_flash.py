from langchain.chat_models import init_chat_model
from common.model.rate_limiter import SlidingWindowRateLimiter
from common.config.env_config import ENV_CONFIG


class DeepSeekFlash:
    def __init__(self):
        self._model = init_chat_model(
            model=ENV_CONFIG.llm.model_name,
            api_key=ENV_CONFIG.llm.api_key,
            base_url=ENV_CONFIG.llm.base_url,
            extra_body={"thinking": {"type": "disabled"}},  # 显式关闭 DeepSeek 思考模式
        )

        self._rate_limiter = SlidingWindowRateLimiter(ENV_CONFIG.llm.rpm)

    async def ainvoke(self, *args, **kwargs):
        await self._rate_limiter.aacquire()
        return await self._model.ainvoke(*args, **kwargs)

    def invoke(self, *args, **kwargs):
        self._rate_limiter.acquire()
        return self._model.invoke(*args, **kwargs)


if __name__ == "__main__":
    import asyncio

    async def main():
        # 示例调用
        response = await DeepSeekFlash().ainvoke("你好")
        print(response.content)

    asyncio.run(main())
