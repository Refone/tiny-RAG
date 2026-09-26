# 环境部署

## Milvus Docker

在 Milvus Github 中可以找到默认配置的 docker-compose.yaml

- https://github.com/milvus-io/milvus
- https://github.com/milvus-io/milvus/blob/master/deployments/docker/standalone/docker-compose.yml

```
wget https://github.com/milvus-io/milvus/raw/refs/heads/master/deployments/docker/standalone/docker-compose.yml
```

稍加调整, 加上 attn、mangodb 服务, 调配成本项目的 [docker compose file](../docker/services.yaml)

用以启动相关服务

```
cd shop-assistant
docker compose -p shop-assistant-services -f ./docker/services.yaml up -d
```
