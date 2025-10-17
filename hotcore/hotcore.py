"""Compatibility layer exposing the historical hotcore API surface."""

from __future__ import annotations

from ._optional import H3_AVAILABLE
from .connection import RedisConnectionManager
from .geospatial import GeospatialManager
from .h3_index import H3IndexManager
from .model import Model
from .relationships import EntityRelationship
from .search import EntitySearch
from .storage import EntityStorage

__all__ = [
    "Model",
    "RedisConnectionManager",
    "EntityStorage",
    "EntityRelationship",
    "EntitySearch",
    "GeospatialManager",
    "H3IndexManager",
    "H3_AVAILABLE",
]
