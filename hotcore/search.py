"""Entity search and indexing helpers."""

from __future__ import annotations

import logging
from typing import Any, Dict, Generator, List, Set

import redis

from .connection import RedisConnectionManager

__all__ = ["EntitySearch"]


class EntitySearch:
    """Provide attribute-based search helpers for entities."""

    logger = logging.getLogger(__name__)

    def __init__(self, connection_manager: RedisConnectionManager) -> None:
        self.connection = connection_manager

    def get_entity_from_index(
        self,
        index_hit: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """Yield entities that are members of the supplied index key."""
        try:
            client = self.connection.get_client()
            self.logger.debug("Index lookup: %s", index_hit)
            index_members: Set[str] = client.smembers(index_hit)
            self.logger.debug("Index hit: %s", index_members)
            for entity_uuid in index_members:
                entity_key = self.connection.get_entity_key(entity_uuid)
                entity: Dict[str, Any] = client.hgetall(entity_key)
                entity["uuid"] = entity_uuid
                yield entity
        except redis.RedisError as exc:
            self.logger.error(
                "Redis error retrieving entities from index %s: %s",
                index_hit,
                exc,
            )
            raise

    def find(self, *args: Any, **kwargs: str) -> Generator[Dict[str, Any], None, None]:
        """Search for entities by attribute values or patterns."""
        del args  # currently unused

        try:
            client = self.connection.get_client()
            filter_list: List[str] = []
            for key, value in kwargs.items():
                if key == "parent":
                    filter_list.append(self.connection.get_children_key(value))
                    continue

                if "*" in value or "?" in value or "[" in value:
                    index_pattern = f"{self.connection.INDEX_PREFIX}{key}:{value}"
                    try:
                        matching_keys = list(
                            client.scan_iter(match=index_pattern, count=1000)
                        )
                    except redis.RedisError as exc:
                        self.logger.error(
                            "Invalid pattern or Redis error scanning keys with pattern "
                            "%s: %s",
                            index_pattern,
                            exc,
                        )
                        matching_keys = []

                    if not matching_keys:
                        self.logger.debug(
                            "No matching keys for pattern: %s", index_pattern
                        )
                        return

                    matching_key_set_name = self.connection.get_unique_set_key()
                    self.logger.debug("Matching keys: %s", matching_keys)
                    self.logger.debug(
                        "Matching key set name: %s", matching_key_set_name
                    )

                    try:
                        if len(matching_keys) == 1:
                            filter_list.append(matching_keys[0])
                        else:
                            union_entity_cnt = client.sunionstore(
                                matching_key_set_name, matching_keys
                            )
                            client.expire(matching_key_set_name, 60)

                            if union_entity_cnt > 0:
                                filter_list.append(matching_key_set_name)
                            else:
                                self.logger.debug(
                                    "No entities in matching keys: %s=%s", key, value
                                )
                                return
                    except redis.RedisError as exc:
                        self.logger.error("Redis error during union operation: %s", exc)
                        try:
                            client.delete(matching_key_set_name)
                        except redis.RedisError:
                            pass
                        return

                    continue

                index_key = self.connection.get_index_key(key, value)
                filter_list.append(index_key)

            if not filter_list:
                self.logger.debug("No filters provided for search")
                return

            try:
                matching_uuids = client.sinter(filter_list)
                for entity_uuid in matching_uuids:
                    self.logger.debug("Hit: %s", entity_uuid)
                    entity_key = self.connection.get_entity_key(entity_uuid)
                    entity = client.hgetall(entity_key)
                    entity["uuid"] = entity_uuid
                    yield entity
            except redis.RedisError as exc:
                self.logger.error(
                    "Redis error during set intersection operation: %s", exc
                )
                raise

        except redis.RedisError as exc:
            self.logger.error("Redis error during find operation: %s", exc)
            raise
