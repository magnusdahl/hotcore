"""Geospatial indexing helpers built on Redis GEO commands."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import redis

from .connection import RedisConnectionManager

__all__ = ["GeospatialManager"]


class GeospatialManager:
    """Manage Redis GEO operations for entities with coordinates."""

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        connection_manager: RedisConnectionManager,
        write_connection_manager: RedisConnectionManager | None = None,
    ) -> None:
        self.connection = connection_manager
        self.write_connection = write_connection_manager or connection_manager

    def _has_coordinates(self, entity: Dict[str, Any]) -> bool:
        """Return True if the entity has valid coordinate fields."""
        return (
            "lat" in entity
            and "long" in entity
            and entity["lat"] is not None
            and entity["long"] is not None
            and isinstance(entity["lat"], (int, float))
            and isinstance(entity["long"], (int, float))
        )

    def _validate_coordinates(self, lat: float, lon: float) -> None:
        """Validate coordinate values."""
        if not (-90 <= lat <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= lon <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")

    def add_to_index(self, entity_uuid: str, entity: Dict[str, Any]) -> None:
        """Insert an entity into the geospatial set if coordinates exist."""
        if not self._has_coordinates(entity):
            return

        entity_type = entity.get("type", "default")

        lat = float(entity["lat"])
        lon = float(entity["long"])
        self._validate_coordinates(lat, lon)

        try:
            client = self.write_connection.get_client()
            geo_key = self.connection.get_geospatial_key(entity_type)
            result = client.geoadd(geo_key, [lon, lat, entity_uuid])

            if result == 1:
                self.logger.debug(
                    "Added entity %s to geospatial index '%s': (%.6f, %.6f)",
                    entity_uuid,
                    entity_type,
                    lat,
                    lon,
                )
            elif result == 0:
                self.logger.debug(
                    "Updated entity %s in geospatial index '%s': (%.6f, %.6f)",
                    entity_uuid,
                    entity_type,
                    lat,
                    lon,
                )
        except redis.RedisError as exc:
            self.logger.error(
                "Redis error adding entity %s to geospatial index '%s': %s",
                entity_uuid,
                entity_type,
                exc,
            )
            raise

    def remove_from_index(self, entity_uuid: str, entity: Dict[str, Any]) -> None:
        """Remove an entity from the geospatial index."""
        entity_type = entity.get("type", "default")
        try:
            client = self.write_connection.get_client()
            geo_key = self.connection.get_geospatial_key(entity_type)
            client.zrem(geo_key, entity_uuid)
        except redis.RedisError as exc:
            self.logger.error(
                "Redis error removing entity %s from geospatial index '%s': %s",
                entity_uuid,
                entity_type,
                exc,
            )
            raise

    def search_bounding_box(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
        entity_type: str = "default",
    ) -> List[str]:
        """Return entity UUIDs inside the provided bounding box."""
        if not (-90 <= min_lat <= max_lat <= 90):
            raise ValueError(
                "Latitude bounds must be between -90 and 90 degrees, with min_lat <= max_lat"
            )
        if not (-180 <= min_lon <= max_lon <= 180):
            raise ValueError(
                "Longitude bounds must be between -180 and 180 degrees, with min_lon <= max_lon"
            )

        try:
            client = self.connection.get_client()
            geo_key = self.connection.get_geospatial_key(entity_type)

            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2
            max_distance = max(abs(max_lat - min_lat), abs(max_lon - min_lon)) * 111

            all_points = client.execute_command(
                "GEORADIUS_RO",
                geo_key,
                center_lon,
                center_lat,
                max_distance,
                "km",
                "WITHCOORD",
            )

            entity_uuids: List[str] = []
            for result in all_points:
                if len(result) < 2:
                    continue

                entity_uuid, coords = result
                lon, lat = coords
                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                except (TypeError, ValueError) as exc:
                    self.logger.warning(
                        "Invalid coordinates for entity %s: lat=%s lon=%s error=%s",
                        entity_uuid,
                        lat,
                        lon,
                        exc,
                    )
                    continue

                if min_lat <= lat_f <= max_lat and min_lon <= lon_f <= max_lon:
                    entity_uuids.append(entity_uuid)

            self.logger.debug(
                "Found %s entities within bounding box " "(%.6f, %.6f) to (%.6f, %.6f)",
                len(entity_uuids),
                min_lat,
                min_lon,
                max_lat,
                max_lon,
            )
            return entity_uuids
        except redis.RedisError as exc:
            self.logger.error("Redis/ValKey error searching by bounding box: %s", exc)
            raise
