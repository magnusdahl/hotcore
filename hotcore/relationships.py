"""Relationship helpers for parent/child lookups."""

from __future__ import annotations

import logging
from typing import Any, Dict, Generator, Optional

import redis

from .connection import RedisConnectionManager

__all__ = ["EntityRelationship"]


class EntityRelationship:
    """Manage traversal of the entity hierarchy."""

    logger = logging.getLogger(__name__)

    def __init__(self, connection_manager: RedisConnectionManager) -> None:
        self.connection = connection_manager

    def get_children(self, parent_uuid: str) -> Generator[Dict[str, Any], None, None]:
        """Yield all direct children for the supplied parent UUID."""
        try:
            client = self.connection.get_client()
            children_key = self.connection.get_children_key(parent_uuid)
            children = client.smembers(children_key)
            if not children:
                self.logger.debug("No children found for parent %s", parent_uuid)
                return

            for child_uuid in children:
                entity_key = self.connection.get_entity_key(child_uuid)
                entity: Dict[str, Any] = client.hgetall(entity_key)
                entity["uuid"] = child_uuid
                yield entity
        except redis.RedisError as exc:
            self.logger.error(
                "Redis error retrieving children for parent %s: %s",
                parent_uuid,
                exc,
            )
            raise

    def get_parent(self, child_uuid: str) -> Dict[str, Any]:
        """Return the parent entity for the supplied child UUID."""
        try:
            client = self.connection.get_client()
            parent_key = self.connection.get_parent_key(child_uuid)
            parent_uuid: Optional[str] = client.get(parent_key)

            if not parent_uuid:
                self.logger.warning(
                    "Parent UUID not found for child %s, returning root",
                    child_uuid,
                )
                return {"uuid": "root"}

            entity_key = self.connection.get_entity_key(parent_uuid)
            entity: Dict[str, Any] = client.hgetall(entity_key)

            if not entity:
                self.logger.warning(
                    "Entity with UUID %s (parent of %s) not found",
                    parent_uuid,
                    child_uuid,
                )

            entity["uuid"] = parent_uuid
            self.logger.debug("Get parent: %s", entity)
            return entity
        except redis.RedisError as exc:
            self.logger.error(
                "Redis error retrieving parent for %s: %s", child_uuid, exc
            )
            raise
