import asyncio
from collections import deque
import time
import threading

from langchain_core.rate_limiters import BaseRateLimiter

class SlidingWindowRateLimiter(BaseRateLimiter):
    """本地滑动窗口限速器(单进程,协程安全)。"""

    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        if max_requests <= 0:
            raise ValueError(f"max_requests must be positive, got {max_requests}")
        if window_seconds <= 0:
            raise ValueError(f"window_seconds must be positive, got {window_seconds}")

        self._max_requests = max_requests
        self._window_seconds = float(window_seconds)

        # 时间戳按升序保存，deque 从头弹出过期项。
        self._timestamps: deque[float] = deque()

        # 一把进程内的锁保护状态。
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        """移除窗口外的旧时间戳。调用方需持有 self._lock。"""
        cutoff = now - self._window_seconds
        ts = self._timestamps
        while ts and ts[0] <= cutoff:
            ts.popleft()

    async def aacquire(self, *, blocking: bool = True) -> bool:
        while True:
            wait_for = 0.0
            with self._lock:
                now = time.monotonic()
                self._prune(now)
                if len(self._timestamps) < self._max_requests:
                    self._timestamps.append(now)
                    return True
                if not blocking:
                    return False
                wait_for = self._timestamps[0] + self._window_seconds - now

            # 在锁外等待，让出事件循环；被取消时 CancelledError 会自然向上抛。
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            # 醒来后重新检查：可能已被别的协程占满。
            await asyncio.sleep(0)  # 让出事件循环，避免忙等待

    def acquire(self, *, blocking: bool = True) -> bool:
        while True:
            wait_for = 0.0
            with self._lock:
                now = time.monotonic()
                self._prune(now)
                if len(self._timestamps) < self._max_requests:
                    self._timestamps.append(now)
                    return True
                if not blocking:
                    return False
                wait_for = self._timestamps[0] + self._window_seconds - now

            if wait_for > 0:
                time.sleep(wait_for)