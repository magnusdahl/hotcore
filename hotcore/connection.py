"""Redis connection and key utilities for HotCore."""

from __future__ import annotations

import logging
import ssl
import uuid
from typing import Any, Mapping, MutableMapping

import redis

__all__ = ["RedisConnectionManager"]


class _ContextSSLConnection(redis.SSLConnection):
    """Redis SSL connection variant that honours a provided ssl.SSLContext."""

    def __init__(self, *args: Any, ssl_context: ssl.SSLContext | None = None, **kwargs: Any) -> None:  # type: ignore[override]
        self._ssl_context = ssl_context
        super().__init__(*args, **kwargs)

    def _wrap_socket_with_ssl(self, sock):  # type: ignore[override]
        if self._ssl_context is not None:
            server_hostname = self.host if self.check_hostname else None
            return self._ssl_context.wrap_socket(sock, server_hostname=server_hostname)
        return super()._wrap_socket_with_ssl(sock)


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
        *,
        ssl_context: ssl.SSLContext | None = None,
        connection_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize the Redis/ValKey connection manager."""
        base_kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "db": db,
            "decode_responses": True,
            "socket_timeout": 10,
            "socket_connect_timeout": 5,
            "retry_on_timeout": True,
            "health_check_interval": 30,
        }

        extra_kwargs: MutableMapping[str, Any] = (
            dict(connection_kwargs) if connection_kwargs else {}
        )

        user_ssl_flag = bool(ssl or extra_kwargs.pop("ssl", False))

        tls_marker_keys = {
            "ssl_certfile",
            "ssl_keyfile",
            "ssl_cert_reqs",
            "ssl_ca_certs",
            "ssl_ca_path",
            "ssl_ca_data",
            "ssl_check_hostname",
            "ssl_password",
            "ssl_validate_ocsp",
            "ssl_validate_ocsp_stapled",
            "ssl_ocsp_context",
            "ssl_ocsp_expected_cert",
            "ssl_min_version",
            "ssl_ciphers",
        }

        tls_requested = (
            user_ssl_flag
            or ssl_context is not None
            or any(key in extra_kwargs for key in tls_marker_keys)
        )

        existing_connection_class = extra_kwargs.get("connection_class")
        if existing_connection_class:
            try:
                connection_class_is_ssl = issubclass(
                    existing_connection_class, redis.SSLConnection  # type: ignore[arg-type]
                )
            except TypeError:
                connection_class_is_ssl = False
            tls_requested = tls_requested or connection_class_is_ssl

        if tls_requested:
            if ssl_context is not None:
                extra_kwargs["connection_class"] = _ContextSSLConnection
                extra_kwargs["ssl_context"] = ssl_context
            else:
                extra_kwargs.setdefault("connection_class", redis.SSLConnection)

            extra_kwargs.setdefault("ssl_cert_reqs", ssl_cert_reqs)
            # ElastiCache Serverless compatibility.
            extra_kwargs.setdefault("ssl_check_hostname", False)

        base_kwargs.update(extra_kwargs)

        self._pool = redis.ConnectionPool(**base_kwargs)

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
