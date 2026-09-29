import json

from minio import Minio

from common.config.env_config import ENV_CONFIG

_minio_client: Minio = None

def _create_minio_client() -> Minio:
    # 创建 Minio 客户端
    client = Minio(
        endpoint=ENV_CONFIG.minio.endpoint,
        access_key=ENV_CONFIG.minio.access_key,
        secret_key=ENV_CONFIG.minio.secret_key,
        secure=ENV_CONFIG.minio.secure,
    )

    # 检查桶是否存在，如果不存在则创建
    if not client.bucket_exists(ENV_CONFIG.minio.bucket_name):
        client.make_bucket(ENV_CONFIG.minio.bucket_name)
        policy = {
            "Version" : "2012-10-17",
            "Statement" : [
                # Statement 中每一条字典记录了一条规则
                {
                    # 这条规则是 允许 ｜ 拒绝
                    "Effect" : "Allow",
                    # 这条规则对谁生效
                    "Principal" : {
                        "AWS" : "*"
                    },
                    # 允许或拒绝的操作
                    "Action" : "s3:GetObject",
                    # 涉及到的资源
                    "Resource" : f"arn:aws:s3:::{ENV_CONFIG.minio.bucket_name}/*",
                },
            ],
        }
        client.set_bucket_policy(ENV_CONFIG.minio.bucket_name, json.dumps(policy))

    return client

def get_minio_client() -> Minio:
    global _minio_client
    if _minio_client is None:
        _minio_client = _create_minio_client()
    return _minio_client

if __name__ == '__main__':
    from rich import print as rprint

    client = get_minio_client()
    rprint(client.list_buckets())
