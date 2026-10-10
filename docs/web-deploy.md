# Web 应用部署

```shell
# 本地开发
uvicorn --app-dir src api.main:app --reload        # 后端 :8000
cd web && npm run dev                              # 前端 :5173 (代理 /api → :8000)

# 一键容器化
docker compose up -d --build
# 前端 :8080，后端 :8000，基础设施 (Milvus/MinIO/Mongo) 一起拉起
```
