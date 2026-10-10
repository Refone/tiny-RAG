# Web 工程的架构

我已经把当前项目摸清楚了。先给结论：你的直觉是对的，`web/` 与 `src/` 同级是标准做法，而且目录已经预留好了。下面是完整规划。

## 当前项目现状（关键事实）

- `src/` 是**扁平源码根**，下面已有 `api/`、`common/`、`processor/`、`utils/` 四个顶层包
- 现有代码的 import 风格是 `from processor...` / `from utils...` / `from common...` —— 也就是**把 `src/` 本身当 `sys.path` 根**，而不是 `from shop_assistant.processor...` 这种标准 src-layout 单包
- `src/api/` 目前只有一个 `test.py`（返回字符串），**还没有真正的 FastAPI app**
- LangGraph 图已经写在 `src/processor/{import_processor, query_processor}/main_graph.py`，编译成了 `import_processor` 等图实例
- `pyproject.toml` 用 `uv` 管理依赖，但**没有 `[build-system]`/包配置**，包不是「安装」出来的，import 依赖 `src` 在 path 上
- `docker/services.yaml` 目前**只有基础设施**（Milvus / MinIO / MongoDB / Attu），还没有应用容器

## 推荐的三层结构（依赖方向单向）

```
web (Vite 前端)
   │  HTTP
   ▼
src/api          —— FastAPI 框架层（HTTP 入口）
   │  调用
   ▼
src/service      —— 业务编排层（"API 逻辑"，新增）
   │  调用
   ▼
src/processor    —— LangGraph 图（状态/节点/编译）
src/common       —— 通用（config/model/client/enum/prompt）
src/utils        —— 工具
```

规则：**api → service → processor → common/utils**，单向调用，不反向、不跨层乱引。

## 完整目录结构

```
shop-assistant/
├── src/                              # Python 后端源码根（sys.path 根）
│   ├── api/                          # ① FastAPI 框架层（已存在，需填充）
│   │   ├── __init__.py
│   │   ├── main.py                   #    app 实例 / lifespan / CORS / 挂载路由
│   │   ├── deps.py                   #    依赖注入（配置、会话、service 实例）
│   │   ├── routers/                  #    路由 = HTTP 端点（只做编解码）
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   ├── import_doc.py
│   │   │   └── query.py
│   │   └── schemas/                  #    Pydantic 请求/响应 DTO
│   │       ├── __init__.py
│   │       ├── chat.py
│   │       └── common.py
│   ├── service/                      # ② 业务编排层（新建）
│   │   ├── __init__.py
│   │   ├── chat_service.py           #    组装图、管历史、astream 流式输出
│   │   ├── import_service.py         #    调用 import_processor 图
│   │   └── query_service.py          #    调用 query_processor 图
│   ├── processor/                    # ③ LangGraph 层（已存在，保持纯图定义）
│   │   ├── import_processor/         #    state.py / nodes/ / main_graph.py
│   │   └── query_processor/
│   ├── common/                       # ④ 通用层（已存在）
│   └── utils/                        # ⑤ 工具层（已存在）
├── web/                              # ⑥ Vite 前端（已存在，待脚手架）
│   ├── src/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts                #    dev proxy: /api → http://localhost:8000
│   ├── Dockerfile                    #    多阶段：node build → nginx
│   └── nginx.conf                    #    静态文件 + /api 反代到 backend:8000
├── docker/
│   ├── services.yaml                 #    基础设施（已存在，保持不动）
│   └── app.Dockerfile                #    后端镜像（新建）
├── docker-compose.yml                #    应用编排（backend + web，引用 infra，新建）
├── pyproject.toml
└── uv.lock
```

## 四个问题的直接回答

### 1. Vite 放哪？→ `web/`（同级，正确）

放 `web/`，它是独立的前端工程（自己的 `package.json`、`vite.config.ts`），和后端 `src/` 完全解耦。关键是 `vite.config.ts` 里配 dev proxy：

```ts
server: {
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true }
  }
}
```

这样开发时前端 `fetch('/api/...')` 直接透传到 FastAPI，规避 CORS。

### 2. FastAPI 逻辑放哪？→ `src/api/`

只放**框架层**：`main.py`（app 实例 + lifespan + CORS）、`routers/`（endpoint）、`schemas/`（DTO）、`deps.py`（依赖注入）。**不要把 LangGraph 调用逻辑写进 router**。

### 3. API 逻辑放哪？→ `src/service/`（新建）

这里的「API 逻辑」我理解为**业务编排层**：负责拿 router 传来的参数、调 `processor/` 里编译好的图（`ainvoke`/`astream`）、做状态转换和会话管理、把结果封装成 service 层结构返回给 router。

> 如果你说的「API 逻辑」其实是指 LangGraph 图本身的节点/边逻辑，那它已经在 `src/processor/` 了，不用动。service 层只是它的「调用者 + 门面」。

### 4. Python import 会不会有问题？→ **会，而且这是最容易踩的坑**

现状是「`src` 当 path 根」的扁平布局。`pytest` 能过，是因为 `pyproject.toml` 里有：

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```

但 **uvicorn 运行时不会读这个配置**。从项目根目录跑 `uvicorn api.main:app`，`src` 不在 `sys.path`，`from processor...` 会直接 `ModuleNotFoundError`。

**推荐方案 A（零改动现有代码，最快跑通）**：统一用 `src` 作为 app 目录：

```bash
# 本地开发
uvicorn --app-dir src api.main:app --reload --port 8000
# 或
PYTHONPATH=src uvicorn api.main:app --reload
```

Docker 里在 `app.Dockerfile` 固定住：

```dockerfile
WORKDIR /app
ENV PYTHONPATH=/app/src
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**方案 B（更规范，但要改代码）**：给 `pyproject.toml` 加 `[build-system]` + 包配置，或干脆迁成标准 src-layout —— `src/shop_assistant/` 单包，import 改成 `from shop_assistant.processor...`。这样无需 PYTHONPATH，最稳，但现有所有 import 都要改一遍。**建议先用 A，等要发 PyPI 包或团队扩大再迁 B。**

⚠️ 额外两个隐藏坑（和 import 同源，都是「根目录识别」问题）：

1. `utils/path_utils.py` 的 `get_project_root()` 靠向上找 `pyproject.toml`/`uv.lock`/`.env` 来定位根目录。**Dockerfile 里必须把这些标记文件一起 COPY 进去**（或 `ENV PROJECT_ROOT=/app`），否则运行时 `PROJECT_ROOT` 解析会抛异常。
2. `src/api/test.py` 这种裸 `test.py` 模块名建议改名（容易和测试约定、以及意外 shadow 冲突），顺手换个有意义的名字。

## Docker 封装建议

- `web/Dockerfile`：多阶段 —— `node:22` build → `nginx:alpine` 托管 `dist/` + `/api` 反代到 `backend:8000`
- `docker/app.Dockerfile`：`python:3.12-slim` + `uv`，COPY `pyproject.toml`、`uv.lock`、`src/`，`uv sync` 后起 uvicorn
- 根目录 `docker-compose.yml`：`backend` + `web` 两个应用容器，并**引用/合并**现有 `docker/services.yaml` 的基础设施（Milvus 等），统一 network 和 env
- 后端依赖重（torch/transformers/mineru 等），镜像会很大，建议考虑 `--no-cache` 分层缓存依赖层

---

要不要我接着把骨架真正搭起来？可以按这个顺序：① 在 `web/` 生成 Vite 脚手架 + proxy 配置 → ② 在 `src/api/` 写 `main.py` + 一个最小 `chat` 路由 → ③ 建 `src/service/` 并接上 `import_processor` 图 → ④ 写两个 Dockerfile + `docker-compose.yml`。你确认下「API 逻辑」是否就是我理解的 service 编排层，我就开工。
