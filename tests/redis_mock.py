"""Redis mocking utilities for tests.

This module provides helpers for using fakeredis in tests.
"""

from typing import Any, Optional

import fakeredis


class RedisMocker:
    """Helper class for mocking Redis with fakeredis.

    This class provides utilities for creating and managing
    a fake Redis server for testing.
    """

    def __init__(self):
        """Initialize the Redis mocker with a fake server."""
        self.server = fakeredis.FakeServer()

    def get_client(self, decode_responses: bool = True) -> fakeredis.FakeRedis:
        """Get a fakeredis client connected to the fake server.

        Args:
            decode_responses: Whether to decode responses to str

        Returns:
            A fakeredis client
        """
        return fakeredis.FakeRedis(
            server=self.server, decode_responses=decode_responses
        )

    def create_connection_pool(self) -> Any:
        """Create a fake connection pool object.

        Returns:
            An object that mimics a redis.ConnectionPool
        """
        # Create a simple object with the necessary attributes
        return type(
            "FakePool",
            (),
            {
                "connection_kwargs": {"host": "fakeredis"},
                "reset": lambda: None,
                "disconnect": lambda: None,
            },
        )()


def patch_redis_connection(connection_manager, mocker, monkeypatch):
    """Patch a RedisConnectionManager to use fakeredis.

    Args:
        connection_manager: The RedisConnectionManager to patch
        mocker: An instance of RedisMocker
        monkeypatch: pytest's monkeypatch fixture
    """
    # Patch the get_client method
    monkeypatch.setattr(connection_manager, "get_client", mocker.get_client)

    # Patch the _pool attribute
    monkeypatch.setattr(connection_manager, "_pool", mocker.create_connection_pool())
