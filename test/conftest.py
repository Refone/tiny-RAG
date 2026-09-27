"""pytest 全局配置与共享 fixture。

测试分级 (三档 marker, 对应三个 --run-* 开关):
    unit        单元测试, mock 所有外部依赖, 默认运行 (无需开关)
    smoke       冒烟测试, 真实 apikey / 网络请求, 默认跳过, 用 --run-smoke 开启
    integration 模块耦合集成测试, 依赖 Milvus / MinIO / LLM 等, 默认跳过, 用 --run-integration 开启

目录约定:
    test/unit           单元测试, 目录结构与 src/ 一一镜像, 文件名 = <模块名>_test.py
    test/smoke          冒烟测试, 验证链路可用性 (真实外部服务, 默认跳过)
    test/integration    集成测试, 模块耦合 (未来使用, 默认跳过)
    test/experimental   试验性脚本, 仅作参考, 不保证可重复
    test/test-data      测试样例文件 (pdf / md / txt)

常用命令:
    uv run pytest                        # 只跑单元测试 (smoke / integration 自动跳过)
    uv run pytest --run-smoke            # 连同冒烟测试一起跑 (真实网络)
    uv run pytest --run-integration      # 连同集成测试一起跑
    uv run pytest test/unit/utils        # 只跑某个目录
    uv run pytest -k doc_type            # 只跑名字匹配的用例
"""

from __future__ import annotations

from pathlib import Path

import pytest

# test/conftest.py -> test/
TEST_ROOT = Path(__file__).resolve().parent


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-unit",
        action="store_true",
        default=True,
        help="运行 unit 单元测试 (默认开启; 占位保留三档对称, 单测不打标、默认即跑)",
    )
    parser.addoption(
        "--run-smoke",
        action="store_true",
        default=False,
        help="运行 smoke 冒烟测试 (真实 apikey / 网络请求), 默认跳过",
    )
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="运行 integration 集成测试 (模块耦合), 默认跳过",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """未开启对应 --run-* 时, 自动跳过 smoke / integration 用例。

    unit 单测是基准档, 不打标、默认运行, 因此这里不做跳过;
    --run-unit 仅作占位保留三档对称。

    注意用 get_closest_marker 而非 `"smoke" in item.keywords`:
    后者会把目录名 (test/smoke) / 模块名也当成 keyword, 误伤同目录下未打标的用例。
    """
    run_smoke = config.getoption("--run-smoke")
    run_integration = config.getoption("--run-integration")

    for item in items:
        if run_smoke is False and item.get_closest_marker("smoke") is not None:
            item.add_marker(pytest.mark.skip(reason="smoke 冒烟测试默认跳过, 加 --run-smoke 开启"))
        if run_integration is False and item.get_closest_marker("integration") is not None:
            item.add_marker(pytest.mark.skip(reason="integration 集成测试默认跳过, 加 --run-integration 开启"))


# --------------------------------------------------------------------------- #
# 路径 fixture
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def project_root() -> Path:
    """项目根目录 (即 pyproject.toml 所在目录)。"""
    return TEST_ROOT.parent


@pytest.fixture(scope="session")
def src_root(project_root: Path) -> Path:
    """源码根目录 src/。"""
    return project_root / "src"


@pytest.fixture(scope="session")
def test_data_dir(project_root: Path) -> Path:
    """测试样例文件目录 test/test-data。"""
    return project_root / "test" / "test-data"


# --------------------------------------------------------------------------- #
# 样例文件 fixture (对应 test/test-data 下的真实文件)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def sample_md(test_data_dir: Path) -> Path:
    """Markdown 样例: 第一章-初识智能体.md"""
    return test_data_dir / "第一章-初识智能体.md"


@pytest.fixture(scope="session")
def sample_pdf(test_data_dir: Path) -> Path:
    """PDF 样例: entropy.pdf"""
    return test_data_dir / "entropy.pdf"


@pytest.fixture(scope="session")
def sample_txt(test_data_dir: Path) -> Path:
    """纯文本样例: test.txt (当前属于不支持的类型, 用于负向用例)"""
    return test_data_dir / "test.txt"
