import asyncio
import base64
from mimetypes import guess_type
import os

from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI

from common.config.env_config import ENV_CONFIG

import time
from collections import deque

class AsyncSlidingWindowRateLimiter:
    """本地滑动窗口限速器(单进程,协程安全)。"""

    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._times: deque[float] = deque()

    async def acquire(self) -> None:
        while True:
            now = time.monotonic()

            # 移除滑出窗口的记录
            while self._times and now - self._times[0] >= self.window_seconds:
                self._times.popleft()

            # 从这里到 return,中间没有 await → 在事件循环里是"原子"的
            if len(self._times) < self.max_requests:
                self._times.append(now)
                return

            wait = self.window_seconds - (now - self._times[0])
            await asyncio.sleep(max(wait, 0.001))


RATE_LIMITER = AsyncSlidingWindowRateLimiter(ENV_CONFIG.vlm.rpm)

VLM = ChatOpenAI(
    model=ENV_CONFIG.vlm.model_name,
    base_url=ENV_CONFIG.vlm.base_url,
    api_key=ENV_CONFIG.vlm.api_key,
)

def encode_image(image_path: str) -> str:
        """把本地图片编码成 Data URL"""
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return f"data:{guess_type(image_path)[0]};base64,{b64}"

if __name__ == '__main__':
    from langchain_core.messages import HumanMessage
    from rich import print as rprint

    local_image_path = f"{os.getcwd()}/test/test-data/RAG.png"
    remote_image_url = "https://pics3.baidu.com/feed/f31fbe096b63f624208f2298bc4e78e91b4ca372.jpeg@f_auto?token=4e343c1319d17140423146fb4bb60b6b"

    response = VLM.invoke([
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "请帮我概括这张图里是什么，总共 50 字以内，用于文档标注。",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": encode_image(local_image_path)},
                },
            ]
        )
    ])
    local_image_desc = response.content
    cost_1 = response.usage_metadata['total_tokens']
    """
    AIMessage(
        content='该图展示基于LangChain的文档问答流程：本地文档经加载、分块、嵌入存入向量库；用户Query通过嵌入与向量库相似度匹配召回相关文本，结合提示模板生成 Prompt，输入LLM（ChatGLM）输出Answer。',
        additional_kwargs={'refusal': None},
        response_metadata={
            'token_usage': {
                'completion_tokens': 60,
                'prompt_tokens': 629,
                'total_tokens': 689,
                'completion_tokens_details': None,
                'prompt_tokens_details': None
            },
            'model_provider': 'openai',
            'model_name': 'Qwen/Qwen3-VL-32B-Instruct',
            'system_fingerprint': '',
            'id': '01a0e74e7ef0694eafc4362fe4fc6c3c',
            'finish_reason': 'stop',
            'logprobs': None
        },
        id='lc_run--01a0e74e-75c5-76f3-b66e-0ec8141c5c86-0',
        tool_calls=[],
        invalid_tool_calls=[],
        usage_metadata={'input_tokens': 629, 'output_tokens': 60, 'total_tokens': 689, 'input_token_details': {}, 'output_token_details': {}}
    )
    """

    response = VLM.invoke([
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "请帮我概括这张图里是什么，总共 50 字以内，用于文档标注。",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": remote_image_url},
                },
            ]
        )
    ])
    remote_image_desc = response.content
    cost2 = response.usage_metadata['total_tokens']

    print(f"本地图片:{local_image_path} \n描述: {local_image_desc}\n消耗: {cost_1} tokens")
    print()
    print(f"远程图片:{remote_image_url} \n描述: {remote_image_desc}\n消耗: {cost2} tokens")