import os

import pytest
import redis

from hotcore import (
    EntityRelationship,
    EntitySearch,
    EntityStorage,
    GeospatialManager,
    Model,
    RedisConnectionManager,
)
from tests.redis_mock import RedisMocker, patch_redis_connection

# Environment variable to control whether to use real Redis or fakeredis
USE_REAL_REDIS = os.environ.get("USE_REAL_REDIS", "").lower() in ("true", "1", "t")


# Define a marker for tests that require a real Redis server
def pytest_configure(config):
    """Add redis_required marker."""
    config.addinivalue_line(
        "markers", "redis_required: mark test as requiring a real Redis server"
    )


# Skip tests marked with redis_required if USE_REAL_REDIS is not set
def pytest_runtest_setup(item):
    """Skip tests that require Redis if USE_REAL_REDIS is not set."""
    if "redis_required" in item.keywords and not USE_REAL_REDIS:
        pytest.skip("Test requires a real Redis server, set USE_REAL_REDIS=true to run")


@pytest.fixture
def redis_host():
    """Return the Redis host to connect to."""
    return os.environ.get("REDIS_HOST", "localhost")


@pytest.fixture
def redis_mocker():
    """Return a RedisMocker instance."""
    return RedisMocker()


@pytest.fixture
def redis_connection_manager(redis_host, redis_mocker, monkeypatch):
    """Return a RedisConnectionManager that uses fakeredis or real Redis."""
    if USE_REAL_REDIS:
        # Use real Redis
        connection_manager = RedisConnectionManager(host=redis_host)
    else:
        # Create a RedisConnectionManager with a dummy host - we'll patch it immediately
        connection_manager = RedisConnectionManager(host="localhost")

        # Patch it to use fakeredis instead of real Redis
        patch_redis_connection(connection_manager, redis_mocker, monkeypatch)

    # Clear all data at the start
    try:
        connection_manager.get_client().flushall()
    except Exception as e:
        pytest.fail(f"Failed to flush Redis: {e}")

    yield connection_manager

    # Clean up after test
    try:
        connection_manager.get_client().flushall()
    except Exception:
        pass  # Ignore errors during cleanup


@pytest.fixture
def model(redis_connection_manager):
    """Return a Model instance that uses the appropriate Redis connection."""
    if USE_REAL_REDIS:
        # Use real Redis
        model = Model(host=redis_connection_manager._pool.connection_kwargs["host"])
    else:
        # Create Model instance without calling __init__
        model = Model.__new__(Model)

        # Initialize the logger
        import logging

        model.logger = logging.getLogger(__name__)

        # Set up the components with our patched connection manager
        model.connection = redis_connection_manager
        model.write_connection = redis_connection_manager
        model.storage = EntityStorage(redis_connection_manager)
        model.relationship = EntityRelationship(redis_connection_manager)
        model.search = EntitySearch(redis_connection_manager)
        model.geospatial = GeospatialManager(
            redis_connection_manager, redis_connection_manager
        )

        # Set h3_index to None for fakeredis tests (H3 functionality not needed for basic tests)
        model.h3_index = None

    # Clear all data at the start
    try:
        model.flush_all()
    except Exception as e:
        pytest.fail(f"Failed to flush data in model fixture: {e}")

    yield model

    # Clean up after test
    try:
        model.flush_all()
    except Exception:
        pass  # Ignore errors during cleanup
