"""
Global pytest configuration and fixtures.
"""

import pytest
import asyncio
import logging
from pathlib import Path

pytest_plugins = ["pytest_asyncio"]


@pytest.fixture(scope="session")
def event_loop_policy():
    """Provide event loop policy."""
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def anyio_backend():
    """Configure anyio backend."""
    return "asyncio"


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async test"
    )


def pytest_addoption(parser):
    parser.addoption(
        "--async-timeout",
        default=5,
        type=int,
        help="Timeout for async tests in seconds"
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


pytest.asyncio_fixture_loop_scope = "function"


@pytest.fixture
def temp_path(tmp_path: Path) -> Path:
    """Provide temporary directory path."""
    return tmp_path


@pytest.fixture
def temp_file(temp_path: Path) -> Path:
    """Provide temporary file path."""
    return temp_path / "test_file.txt"


@pytest.fixture
def logger() -> logging.Logger:
    """Provide test logger."""
    return logging.getLogger("test")
