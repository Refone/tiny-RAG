"""单元测试: src/utils/path_utils.py

被测对象:
    get_project_root    向上查找项目标记 (pyproject.toml / uv.lock / .env)
    get_src_root        src 目录 (不存在时抛 FileNotFoundError)
    from_project_root   基于项目根目录拼接路径
    get_path_dir        取当前文件的上 N 级目录

TODO: 补充用例
    - get_project_root() 命中含 pyproject.toml 的目录
    - 设置 PROJECT_ROOT 环境变量时优先采用它
    - lru_cache 生效 (同进程多次调用返回同一对象), 用例间注意 cache_clear()
    - get_src_root() 在 src 缺失时抛 FileNotFoundError
    - from_project_root("test/test-data") 能拼出真实存在的目录
"""
