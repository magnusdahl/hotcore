"""Facade class that coordinates the HotCore subsystems."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Generator, Iterable, List, Optional

from ._optional import H3_AVAILABLE
from .connection import RedisConnectionManager
from .geospatial import GeospatialManager
from .h3_index import H3IndexManager
from .relationships import EntityRelationship
from .search import EntitySearch
from .storage import EntityStorage

__all__ = ["Model"]


class Model:
    """Facade that wires storage, relationship, search, and indexing services."""

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        host: str,
        port: int = 6379,
        db: int = 0,
        ssl: bool = False,
        ssl_cert_reqs: str = "required",
        write_host: Optional[str] = None,
        write_port: Optional[int] = None,
    ) -> None:
        self.connection = RedisConnectionManager(host, port, db, ssl, ssl_cert_reqs)

        write_host = write_host or host
        write_port = write_port or port
        self.write_connection = (
            RedisConnectionManager(write_host, write_port, db, ssl, ssl_cert_reqs)
            if (write_host != host or write_port != port)
            else self.connection
        )

        self.storage = EntityStorage(self.connection)
        self.relationship = EntityRelationship(self.connection)
        self.search = EntitySearch(self.connection)
        self.geospatial = GeospatialManager(self.connection, self.write_connection)

        self.h3_index: Optional[H3IndexManager]
        if H3_AVAILABLE:
            self.h3_index = H3IndexManager(self.connection)
        else:
            self.h3_index = None

    def flush_all(self) -> None:
        """Delete every key stored in the configured Redis database."""
        self.connection.flush_all()

    @staticmethod
    def init(entity: Dict[str, Any] | None) -> Dict[str, Any]:
        """Return a shallow copy of the entity with a UUID value ensured."""
        if entity is None or not isinstance(entity, dict):
            entity = {}
        else:
            entity = entity.copy()

        if "uuid" not in entity:
            entity["uuid"] = str(uuid.uuid4())
        elif not isinstance(entity["uuid"], str):
            entity["uuid"] = str(entity["uuid"])

        return entity

    def create(self, parent_uuid: str, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity, updating geospatial and H3 indexes."""
        entity = entity.copy()

        if self.h3_index:
            try:
                self.h3_index.prepare_entity(entity)
            except Exception as exc:  # pragma: no cover - diagnostic path
                self.logger.debug(
                    "Unable to prepare H3 index for entity %s: %s",
                    entity.get("uuid"),
                    exc,
                )

        result = self.storage.create(parent_uuid, entity)

        # Best-effort geospatial indexing
        try:
            self.geospatial.add_to_index(entity["uuid"], entity)
        except Exception as exc:  # pragma: no cover - log-only
            self.logger.warning(
                "Could not add entity %s to geospatial index: %s",
                entity["uuid"],
                exc,
            )

        if self.h3_index:
            try:
                self.h3_index.add_to_index(entity["uuid"], entity)
            except Exception as exc:  # pragma: no cover - log-only
                self.logger.warning(
                    "Could not add entity %s to H3 index: %s",
                    entity["uuid"],
                    exc,
                )

        return result

    def _remove_from_all_geospatial_indexes(self, entity_uuid: str) -> None:
        """Remove an entity from common geospatial indexes if present."""
        try:
            client = self.connection.get_client()
        except Exception as exc:  # pragma: no cover - log-only
            self.logger.warning(
                "Error acquiring Redis client while removing %s from geospatial indexes: %s",
                entity_uuid,
                exc,
            )
            return

        common_types = [
            "user",
            "office",
            "business",
            "restaurant",
            "location",
            "point",
            "default",
        ]

        for entity_type in common_types:
            geo_key = self.connection.get_geospatial_key(entity_type)
            try:
                removed = client.zrem(geo_key, entity_uuid)
                if removed:
                    self.logger.debug(
                        "Removed entity %s from geospatial key '%s'",
                        entity_uuid,
                        geo_key,
                    )
                    break
            except Exception as exc:  # pragma: no cover - log-only
                self.logger.debug(
                    "Error removing entity %s from geospatial key '%s': %s",
                    entity_uuid,
                    geo_key,
                    exc,
                )

    def get(self, entity_uuid: str) -> Dict[str, Any]:
        """Return an entity by UUID."""
        return self.storage.get(entity_uuid)

    def apply(self, change: Dict[str, Any]) -> None:
        """Apply updates to an entity and refresh related indexes."""
        change = change.copy()
        entity_uuid = change["uuid"]
        previous_entity: Optional[Dict[str, Any]] = None

        try:
            previous_entity = self.storage.get(entity_uuid)
        except Exception as exc:  # pragma: no cover - log-only
            self.logger.debug(
                "Unable to load entity %s prior to apply: %s", entity_uuid, exc
            )

        if self.h3_index:
            try:
                self.h3_index.prepare_update(change, previous_entity)
            except Exception as exc:  # pragma: no cover - log-only
                self.logger.debug(
                    "Unable to prepare H3 update for entity %s: %s",
                    entity_uuid,
                    exc,
                )

        self.storage.apply(change)

        updated_entity: Optional[Dict[str, Any]] = None
        try:
            updated_entity = self.storage.get(entity_uuid)
        except Exception as exc:  # pragma: no cover - log-only
            self.logger.debug(
                "Unable to load entity %s after apply: %s", entity_uuid, exc
            )

        # Refresh geospatial index if coordinates or type changed
        if any(key in change for key in ("lat", "long", "type")):
            try:
                if updated_entity and self.geospatial._has_coordinates(updated_entity):
                    self.geospatial.add_to_index(entity_uuid, updated_entity)
                else:
                    self._remove_from_all_geospatial_indexes(entity_uuid)
            except Exception as exc:  # pragma: no cover - log-only
                self.logger.warning(
                    "Failed to update geospatial index for %s: %s",
                    entity_uuid,
                    exc,
                )

        if self.h3_index:
            try:
                if updated_entity:
                    self.h3_index.add_to_index(entity_uuid, updated_entity)
                else:
                    self.h3_index.remove_from_index(entity_uuid)
            except Exception as exc:  # pragma: no cover - log-only
                self.logger.warning(
                    "Failed to update H3 index for %s: %s", entity_uuid, exc
                )

    def delete(self, entity: Dict[str, Any]) -> None:
        """Delete an entity and clean up related indexes."""
        entity_uuid = entity["uuid"]

        try:
            self.storage.delete(entity)
        finally:
            try:
                self.geospatial.remove_from_index(entity_uuid, entity)
            except Exception as exc:  # pragma: no cover - log-only
                self.logger.debug(
                    "Error removing entity %s from geospatial index: %s",
                    entity_uuid,
                    exc,
                )
                self._remove_from_all_geospatial_indexes(entity_uuid)

            if self.h3_index:
                try:
                    self.h3_index.remove_from_index(entity_uuid)
                except Exception as exc:  # pragma: no cover - log-only
                    self.logger.debug(
                        "Error removing entity %s from H3 index: %s",
                        entity_uuid,
                        exc,
                    )

    def get_children(self, parent_uuid: str) -> Generator[Dict[str, Any], None, None]:
        """Yield child entities for the supplied parent UUID."""
        return self.relationship.get_children(parent_uuid)

    def get_parent(self, child_uuid: str) -> Dict[str, Any]:
        """Return the parent entity for the supplied child UUID."""
        return self.relationship.get_parent(child_uuid)

    def find(self, **criteria: Any) -> Iterable[Dict[str, Any]]:
        """Return entities that match the provided index criteria."""
        return self.search.find(**criteria)

    def search_bounding_box(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        entity_type: str = "default",
    ) -> List[Dict[str, Any]]:
        """Return entities within the provided bounding box."""
        entity_uuids = self.geospatial.search_bounding_box(
            min_lat, max_lat, min_lon, max_lon, entity_type
        )

        entities: List[Dict[str, Any]] = []
        for entity_uuid in entity_uuids:
            try:
                entity = self.storage.get(entity_uuid)
            except Exception as exc:  # pragma: no cover - log-only
                self.logger.debug(
                    "Failed to load entity %s during geospatial search: %s",
                    entity_uuid,
                    exc,
                )
                continue
            if entity:
                entities.append(entity)
        return entities
