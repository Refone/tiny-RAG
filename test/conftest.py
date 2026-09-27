"""pytest 全局配置与共享 fixture。

目录约定:
    test/unit           单元测试, 目录结构与 src/ 一一镜像, 文件名 = <模块名>_test.py
    test/integration    集成测试, 依赖 Milvus / MinerU / MinIO / LLM 等外部服务, 默认跳过
    test/experimental   试验性脚本, 仅作参考, 不保证可重复
    test/test-data      测试样例文件 (pdf / md / txt)

常用命令:
    uv run pytest                        # 全部单元测试 (集成测试自动跳过)
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
        "--run-integration",
        action="store_true",
        default=False,
        help="运行标记为 integration 的测试 (默认跳过)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """未显式开启 --run-integration 时, 自动跳过 integration 用例。"""
    if config.getoption("--run-integration"):
        return
    skip_integration = pytest.mark.skip(reason="集成测试默认跳过, 加 --run-integration 开启")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


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
