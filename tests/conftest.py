import os
import ssl

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
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_USE_TLS = os.environ.get("REDIS_USE_TLS", "").lower() in ("true", "1", "t")
REDIS_TLS_CA_CERT = os.environ.get("REDIS_TLS_CA_CERT")
REDIS_TLS_CLIENT_CERT = os.environ.get("REDIS_TLS_CLIENT_CERT")
REDIS_TLS_CLIENT_KEY = os.environ.get("REDIS_TLS_CLIENT_KEY")
REDIS_TLS_CHECK_HOSTNAME = (
    os.environ.get("REDIS_TLS_CHECK_HOSTNAME", "false").lower() in ("true", "1", "t")
)

TLS_CONTEXT = None
TLS_CONNECTION_KWARGS: dict[str, object] | None = None

if REDIS_USE_TLS:
    TLS_CONTEXT = ssl.create_default_context()
    if REDIS_TLS_CA_CERT:
        TLS_CONTEXT.load_verify_locations(REDIS_TLS_CA_CERT)
    if REDIS_TLS_CLIENT_CERT and REDIS_TLS_CLIENT_KEY:
        TLS_CONTEXT.load_cert_chain(REDIS_TLS_CLIENT_CERT, REDIS_TLS_CLIENT_KEY)
    TLS_CONNECTION_KWARGS = {"ssl_check_hostname": REDIS_TLS_CHECK_HOSTNAME}


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
        connection_manager = RedisConnectionManager(
            host=redis_host,
            port=REDIS_PORT,
            ssl_context=TLS_CONTEXT,
            connection_kwargs=TLS_CONNECTION_KWARGS,
        )
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
        host = redis_connection_manager._pool.connection_kwargs["host"]
        model = Model(
            host=host,
            port=REDIS_PORT,
            ssl_context=TLS_CONTEXT,
            connection_kwargs=TLS_CONNECTION_KWARGS,
            write_host=host,
            write_port=REDIS_PORT,
            write_ssl_context=TLS_CONTEXT,
            write_connection_kwargs=TLS_CONNECTION_KWARGS,
        )
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
