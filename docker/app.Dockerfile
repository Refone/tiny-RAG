FROM python:3.12-slim

# 安装 uv (从官方镜像拷贝静态二进制)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONPATH=/app/src \
    PROJECT_ROOT=/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 依赖层 (可缓存): 只复制依赖清单, 避免源码改动触发重装 torch 等重依赖
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 源码层
COPY src ./src

EXPOSE 8000

# 直接用 venv 内的 uvicorn, 避免 uv run 重新探测/构建项目
CMD [".venv/bin/uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
