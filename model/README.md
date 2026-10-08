# 需要拉取到本地的模型

## BGE-M3 嵌入模型

- https://hf-mirror.com/BAAI/bge-m3/tree/main?clone=true

- https://huggingface.co/BAAI/bge-m3/tree/main?clone=true

- https://modelscope.cn/models/BAAI/bge-m3/files

```shell
# 1. 关闭 Xet（必须）
export HF_HUB_DISABLE_XET=1

# 2. 确保镜像端点已设置
export HF_ENDPOINT=https://hf-mirror.com

# 3. 重新下载，并排除无关文件
hf download BAAI/bge-m3 --local-dir ./bge-m3 --exclude ".DS_Store" --exclude "imgs/*"
```
