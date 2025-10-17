"""Entity storage primitives."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import redis

from .connection import RedisConnectionManager

__all__ = ["EntityStorage"]


class EntityStorage:
    """CRUD + indexing management for entities."""

    logger = logging.getLogger(__name__)

    NON_INDEXABLE_FIELDS = {
        "status_history",
        "station_data",
        "connector_data",
        "raw_data",
        "metadata",
        "logs",
        "events",
    }

    def __init__(self, connection_manager: RedisConnectionManager) -> None:
        self.connection = connection_manager

    def get(self, entity_uuid: str) -> Dict[str, Any]:
        """Return an entity by UUID."""
        entity_key = self.connection.get_entity_key(entity_uuid)
        try:
            client = self.connection.get_client()
            entity: Dict[str, Any] = client.hgetall(entity_key)
            if not entity:
                self.logger.warning("Entity with UUID %s not found", entity_uuid)
            entity["uuid"] = entity_uuid
            self.logger.debug("Get: %s", entity)
            return entity
        except redis.RedisError as exc:
            self.logger.error("Redis error retrieving entity %s: %s", entity_uuid, exc)
            raise

    def create(self, parent_uuid: str, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create and store a new entity with the given parent."""
        entity_uuid = entity.get("uuid")
        if entity_uuid is None:
            raise TypeError(
                "entity must be a dictionary (dict) containing the key 'uuid'"
            )

        try:
            client = self.connection.get_client()
            entity_key = self.connection.get_entity_key(entity_uuid)
            parent_key = self.connection.get_parent_key(entity_uuid)
            children_key = self.connection.get_children_key(parent_uuid)

            with client.pipeline() as pipe:
                pipe.multi()

                entity_copy = entity.copy()
                del entity_copy["uuid"]

                pipe.hset(entity_key, mapping=entity_copy)

                for key, value in entity_copy.items():
                    if key in self.NON_INDEXABLE_FIELDS:
                        continue
                    index_key = self.connection.get_index_key(key, value)
                    pipe.sadd(index_key, entity_uuid)

                pipe.set(parent_key, parent_uuid)
                pipe.sadd(children_key, entity_uuid)

                pipe.execute()
                self.logger.info(
                    "Created entity %s with parent %s", entity_uuid, parent_uuid
                )
                return entity
        except redis.RedisError as exc:
            self.logger.error("Redis error creating entity %s: %s", entity_uuid, exc)
            raise

    def _update_entity_indexes(
        self,
        pipe: redis.client.Pipeline,
        entity_uuid: str,
        old_entity: Dict[str, Any],
        updates: Dict[str, Any],
    ) -> None:
        """Update secondary indexes affected by the change set."""
        if not updates:
            return

        entity_key = self.connection.get_entity_key(entity_uuid)
        pipe.hset(entity_key, mapping=updates)

        for key, value in updates.items():
            if key in self.NON_INDEXABLE_FIELDS:
                continue

            if key in old_entity:
                old_value = old_entity[key]
                if old_value is not None:
                    old_index_key = self.connection.get_index_key(key, old_value)
                    pipe.srem(old_index_key, entity_uuid)

            new_index_key = self.connection.get_index_key(key, value)
            pipe.sadd(new_index_key, entity_uuid)

    def _remove_entity_attributes(
        self,
        pipe: redis.client.Pipeline,
        entity_uuid: str,
        old_entity: Dict[str, Any],
        keys_to_remove: List[str],
    ) -> None:
        """Remove attributes from the entity and clean their indexes."""
        entity_key = self.connection.get_entity_key(entity_uuid)

        for key in keys_to_remove:
            if key not in old_entity:
                continue

            old_value = old_entity[key]
            pipe.hdel(entity_key, key)

            if key in self.NON_INDEXABLE_FIELDS:
                continue

            index_key = self.connection.get_index_key(key, old_value)
            pipe.srem(index_key, entity_uuid)
            self.logger.debug("Deleting attribute: %s", key)

    def apply(self, change: Dict[str, Any]) -> None:
        """Apply attribute changes to an entity."""
        if "uuid" not in change:
            raise KeyError("The change dictionary must contain a 'uuid' key")

        entity_uuid = change["uuid"]
        watch_key = self.connection.get_watch_key(entity_uuid)
        entity_key = self.connection.get_entity_key(entity_uuid)

        try:
            client = self.connection.get_client()
            with client.pipeline() as pipe:
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    try:
                        pipe.watch(watch_key)
                        old_entity: Dict[str, Any] = pipe.hgetall(entity_key)
                        if not old_entity:
                            self.logger.warning(
                                "Entity with UUID %s not found during apply operation",
                                entity_uuid,
                            )

                        self.logger.debug("Current entity: %s", old_entity)

                        pipe.multi()
                        pipe.set(watch_key, "")

                        keys_to_remove = [
                            key
                            for key, value in change.items()
                            if value is None and key != "uuid"
                        ]
                        updated_values = {
                            key: value
                            for key, value in change.items()
                            if value is not None and key != "uuid"
                        }

                        self.logger.debug("Updated values: %s", updated_values)

                        self._remove_entity_attributes(
                            pipe, entity_uuid, old_entity, keys_to_remove
                        )
                        self._update_entity_indexes(
                            pipe, entity_uuid, old_entity, updated_values
                        )

                        pipe.execute()
                        self.logger.info(
                            "Apply operation executed successfully for entity %s",
                            entity_uuid,
                        )
                        break
                    except redis.WatchError:
                        retry_count += 1
                        self.logger.warning(
                            "WatchError during apply of %s, retry %s/%s",
                            entity_uuid,
                            retry_count,
                            max_retries,
                        )
                        if retry_count >= max_retries:
                            self.logger.error(
                                "Max retries (%s) reached for apply operation on %s",
                                max_retries,
                                entity_uuid,
                            )
                            raise
                else:
                    self.logger.error(
                        "Unable to complete apply for %s after %s retries",
                        entity_uuid,
                        max_retries,
                    )
        except redis.RedisError as exc:
            self.logger.error(
                "Redis error during apply operation on entity %s: %s",
                entity_uuid,
                exc,
            )
            raise

    def delete(self, entity: Dict[str, Any]) -> None:
        """Delete an entity and clean all related state."""
        if "uuid" not in entity:
            raise KeyError("The entity dictionary must contain a 'uuid' key")

        entity_uuid = entity["uuid"]
        watch_key = self.connection.get_watch_key(entity_uuid)
        entity_key = self.connection.get_entity_key(entity_uuid)
        parent_key = self.connection.get_parent_key(entity_uuid)
        children_key = self.connection.get_children_key(entity_uuid)

        try:
            client = self.connection.get_client()
            with client.pipeline() as pipe:
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    try:
                        pipe.watch(watch_key)
                        old_entity: Dict[str, Any] = pipe.hgetall(entity_key)
                        if not old_entity:
                            self.logger.warning(
                                "Entity with UUID %s not found during delete operation",
                                entity_uuid,
                            )

                        parent_uuid = pipe.get(parent_key)

                        # CRITICAL: Get children BEFORE pipe.multi() is called
                        # pipe.smembers() returns actual data when called before multi()
                        # but returns a command object if called after multi()
                        child_uuids = pipe.smembers(children_key)

                        self.logger.debug("Current entity: %s", old_entity)

                        pipe.multi()
                        pipe.delete(entity_key)

                        for key, value in old_entity.items():
                            if key in self.NON_INDEXABLE_FIELDS:
                                continue
                            index_key = self.connection.get_index_key(key, value)
                            pipe.srem(index_key, entity_uuid)

                        pipe.delete(watch_key)
                        pipe.delete(parent_key)

                        if parent_uuid:
                            parent_children_key = self.connection.get_children_key(
                                parent_uuid
                            )
                            pipe.srem(parent_children_key, entity_uuid)

                        for child_uuid in child_uuids:
                            child_parent_key = self.connection.get_parent_key(
                                child_uuid
                            )
                            pipe.set(child_parent_key, parent_uuid or "root")

                        pipe.delete(children_key)

                        pipe.execute()
                        self.logger.info("Deleted entity %s", entity_uuid)
                        break
                    except redis.WatchError:
                        retry_count += 1
                        self.logger.warning(
                            "WatchError during delete of %s, retry %s/%s",
                            entity_uuid,
                            retry_count,
                            max_retries,
                        )
                        if retry_count >= max_retries:
                            self.logger.error(
                                "Max retries (%s) reached for delete operation on %s",
                                max_retries,
                                entity_uuid,
                            )
                            raise
                else:
                    self.logger.error(
                        "Unable to complete delete for %s after %s retries",
                        entity_uuid,
                        max_retries,
                    )
        except redis.RedisError as exc:
            self.logger.error(
                "Redis error during delete operation on entity %s: %s",
                entity_uuid,
                exc,
            )
            raise
