"""Pytest configuration for tests requiring a real Redis server."""

import logging
import os

import pytest

from hotcore import Model

# Configure logging
logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.DEBUG
)


REAL_REDIS_TEST_DIR = os.path.abspath(os.path.dirname(__file__))


def _is_real_redis_test(item):
    """Return True when the collected item lives under tests/real_redis/."""
    # pytest < 8 exposes fspath, pytest >= 8 prefers path
    path_obj = getattr(item, "path", None) or getattr(item, "fspath", None)
    if path_obj is None:
        return False
    try:
        raw_path = os.fspath(path_obj)
    except TypeError:
        raw_path = str(path_obj)
    item_path = os.path.abspath(raw_path)
    try:
        return (
            os.path.commonpath([item_path, REAL_REDIS_TEST_DIR]) == REAL_REDIS_TEST_DIR
        )
    except ValueError:
        return False


# Skip only the real_redis tests when USE_REAL_REDIS is not set
def pytest_collection_modifyitems(config, items):
    """Skip real Redis tests if USE_REAL_REDIS is not set."""
    use_real_redis = os.environ.get("USE_REAL_REDIS", "").lower() in ("true", "1", "t")
    if use_real_redis:
        return

    skip_marker = pytest.mark.skip(
        reason="Test requires real Redis, set USE_REAL_REDIS=true to run"
    )
    for item in items:
        if _is_real_redis_test(item):
            item.add_marker(skip_marker)


@pytest.fixture
def redis_host():
    """Return the Redis host to connect to."""
    return os.environ.get("REDIS_HOST", "localhost")


# Fixture to ensure we have a clean Redis environment for each test
@pytest.fixture(autouse=True)
def clean_redis_each_test(model):
    """Ensure Redis is clean before and after each test."""
    # Before each test, flush all data
    try:
        model.flush_all()
    except Exception as e:
        pytest.fail(f"Failed to flush Redis at test start: {e}")

    yield model

    # After each test, clean up
    try:
        model.flush_all()
    except Exception:
        pass  # Ignore cleanup errors
