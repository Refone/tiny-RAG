import json
from mimetypes import guess_type
from minio import Minio
from minio.deleteobjects import DeleteObject
from utils.logging_utils import logger
from common.config.env_config import ENV_CONFIG


class RagMinioClient:
    def __init__(self):
        self.bucket_name = ENV_CONFIG.minio.bucket_name
        self.endpoint = ENV_CONFIG.minio.endpoint
        self.access_key = ENV_CONFIG.minio.access_key
        self.secret_key = ENV_CONFIG.minio.secret_key
        self.secure = ENV_CONFIG.minio.secure

        self._minio = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

        # 检查桶是否存在，如果不存在则创建
        if not self._minio.bucket_exists(self.bucket_name):
            self._minio.make_bucket(self.bucket_name)
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    # Statement 中每一条字典记录了一条规则
                    {
                        # 这条规则是 允许 ｜ 拒绝
                        "Effect": "Allow",
                        # 这条规则对谁生效
                        "Principal": {"AWS": "*"},
                        # 允许或拒绝的操作
                        "Action": "s3:GetObject",
                        # 涉及到的资源
                        "Resource": f"arn:aws:s3:::{self.bucket_name}/*",
                    },
                ],
            }
            self._minio.set_bucket_policy(self.bucket_name, json.dumps(policy))

    def clear_dir_if_exist(self, prefix: str) -> int:
        """
        清除路径下的所有文件(保留文件夹)
        Args:
            prefix: 路径(文件夹) 例如:"upload-images/hak180产品安全手册"
        Returns:
            成功删除的元素个数
        """
        objects = self._minio.list_objects(
            bucket_name=self.bucket_name, prefix=prefix, recursive=True
        )
        delete_objects = [DeleteObject(obj.object_name) for obj in objects]
        delete_cnt = len(delete_objects)
        errors = self._minio.remove_objects(
            bucket_name=self.bucket_name,
            delete_object_list=delete_objects,
        )
        # 删除逻辑放在了迭代器的 __next__ 方法中
        # 所以要想办法调用 errors 的迭代器
        # 在这个迭代器或者说生成器中，只有删除失败才会“生成”元素
        for error in errors:
            delete_cnt -= 1
            logger.info(f"删除失败 {error}")

        return delete_cnt

    def upload_file(self, prefix: str, as_name: str, file_path: str) -> str:
        """上传一个文件

        Args:
            prefix: 云端路径
            as_name: 云端文件名
            file_path: 本地文件路径
        Returns:
            云端文件 url
        """
        res = self._minio.fput_object(
            bucket_name=self.bucket_name,
            object_name=prefix + "/" + as_name,
            file_path=file_path,
            content_type=guess_type(file_path)[0],
        )

        from rich import print as rprint

        rprint(res)

        return f"http://{self.endpoint}/{self.bucket_name}/{prefix}/{as_name}"


if __name__ == "__main__":
    from rich import print as rprint

    client = RagMinioClient()
    rprint(client._minio.list_buckets())
