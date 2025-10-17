"""HotCore: A Redis-based hierarchical entity model for application data management.

This package provides a data model implementation using Redis as the backend.
It manages a hierarchical tree structure of entities with parent-child relationships
and supports indexing of entity attributes for efficient searching.
"""

from ._version import __version__
from .hotcore import (
    H3_AVAILABLE,
    EntityRelationship,
    EntitySearch,
    EntityStorage,
    GeospatialManager,
    H3IndexManager,
    Model,
    RedisConnectionManager,
)

__all__ = [
    "Model",
    "RedisConnectionManager",
    "EntityStorage",
    "EntityRelationship",
    "EntitySearch",
    "GeospatialManager",
    "H3IndexManager",
    "H3_AVAILABLE",
    "__version__",
]
