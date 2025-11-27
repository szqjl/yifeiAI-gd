"""
Pytest配置文件

提供测试fixtures和配置。
"""

import pytest
import tempfile
import os
from hypothesis import settings


# 配置hypothesis
settings.register_profile("default", max_examples=100)
settings.load_profile("default")


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_file():
    """创建临时文件用于测试"""
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)
