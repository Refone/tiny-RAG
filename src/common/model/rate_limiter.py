import asyncio
from collections import deque
import time

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
