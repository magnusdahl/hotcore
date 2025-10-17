"""Redis connection and key utilities for HotCore."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import redis

__all__ = ["RedisConnectionManager"]


class RedisConnectionManager:
    """Manages Redis/ValKey connections and provides key generation helpers."""

    # Redis key prefixes
    ENTITY_PREFIX = "e:"
    INDEX_PREFIX = "i:"
    PARENT_PREFIX = "p:"
    CHILDREN_PREFIX = "c:"
    FIND_UNIQUE_PREFIX = "u:"
    WATCH_LOCK_PREFIX = "w:"
    GEOSPATIAL_PREFIX = "geo:"
    POI_PREFIX = "poi:"
    H3_INDEX_PREFIX = "h3:"

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        host: str,
        port: int = 6379,
        db: int = 0,
        ssl: bool = False,
        ssl_cert_reqs: str = "required",
    ) -> None:
        """Initialize the Redis/ValKey connection manager."""
        connection_kwargs = {
            "host": host,
            "port": port,
            "db": db,
            "decode_responses": True,
            "socket_timeout": 10,
            "socket_connect_timeout": 5,
            "retry_on_timeout": True,
            "health_check_interval": 30,
        }

        if ssl:
            connection_kwargs["ssl"] = True
            connection_kwargs["ssl_cert_reqs"] = ssl_cert_reqs
            # ElastiCache Serverless compatibility.
            connection_kwargs["ssl_check_hostname"] = False

        self._pool = redis.ConnectionPool(**connection_kwargs)

    def get_client(self) -> redis.Redis:
        """Return a Redis client that uses the configured connection pool."""
        return redis.Redis(connection_pool=self._pool)

    def flush_all(self) -> None:
        """Delete all keys in the target Redis database."""
        try:
            self.get_client().flushall()
        except redis.RedisError as exc:
            self.logger.error("Redis error during flush_all: %s", exc)
            raise

    def get_entity_key(self, entity_uuid: str) -> str:
        """Return the hash key for an entity."""
        return f"{self.ENTITY_PREFIX}{entity_uuid}"

    def get_watch_key(self, entity_uuid: str) -> str:
        """Return the optimistic locking watch key for an entity."""
        return f"{self.WATCH_LOCK_PREFIX}{entity_uuid}"

    def get_parent_key(self, entity_uuid: str) -> str:
        """Return the key that stores the entity's parent pointer."""
        return f"{self.PARENT_PREFIX}{entity_uuid}"

    def get_children_key(self, entity_uuid: str) -> str:
        """Return the key that stores a parent's children set."""
        return f"{self.CHILDREN_PREFIX}{entity_uuid}"

    def get_index_key(self, attribute: str, value: Any) -> str:
        """Return the secondary-index key for a specific attribute value."""
        return f"{self.INDEX_PREFIX}{attribute}:{value}"

    def get_unique_set_key(self) -> str:
        """Return a unique Redis key for temporary sets."""
        return f"{self.FIND_UNIQUE_PREFIX}{uuid.uuid4()}"

    def get_geospatial_key(self, entity_type: str = "default") -> str:
        """Return the geospatial index key for an entity type."""
        return f"{self.GEOSPATIAL_PREFIX}{entity_type}"

    def get_h3_index_key(
        self,
        cell: str,
        resolution: int,
        entity_type: str = "default",
    ) -> str:
        """Return the H3 index key for a cell/entity-type combination."""
        return f"{self.H3_INDEX_PREFIX}r{resolution}:{entity_type}:{cell}"
