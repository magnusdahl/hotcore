"""HotCore: A Redis-based hierarchical entity model for application data management.

This package provides a data model implementation using Redis as the backend.
It manages a hierarchical tree structure of entities with parent-child relationships
and supports indexing of entity attributes for efficient searching.
"""

from .model import (
    Model,
    RedisConnectionManager,
    EntityStorage,
    EntityRelationship,
    EntitySearch
)

__version__ = "0.1.0"
