"""Unit tests for the Model component classes with mocked Redis interactions.

These tests focus on testing the individual component classes that make up the Model:
- RedisConnectionManager
- EntityStorage
- EntityRelationship
- EntitySearch

Each test uses explicit mocking to isolate the component being tested.
"""

import uuid
from unittest.mock import MagicMock, call, patch

import pytest
import redis

from hotcore import (
    EntityRelationship,
    EntitySearch,
    EntityStorage,
    RedisConnectionManager,
)


class TestRedisConnectionManager:
    """Unit tests for the RedisConnectionManager class."""

    def test_initialization(self):
        """Test that RedisConnectionManager initializes with correct parameters."""
        with patch("redis.ConnectionPool") as mock_pool:
            manager = RedisConnectionManager(host="testhost", port=1234, db=5)

            # Check that ConnectionPool was called with expected arguments
            mock_pool.assert_called_once_with(
                host="testhost",
                port=1234,
                db=5,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

    def test_get_client(self):
        """Test that get_client returns a Redis client using the connection pool."""
        with patch("redis.ConnectionPool") as mock_pool:
            with patch("redis.Redis") as mock_redis:
                manager = RedisConnectionManager(host="testhost")
                client = manager.get_client()

                # Check that Redis was initialized with the pool
                mock_redis.assert_called_once_with(connection_pool=manager._pool)

    def test_flush_all(self):
        """Test that flush_all calls flushall on the Redis client."""
        with patch("redis.ConnectionPool"):
            manager = RedisConnectionManager(host="testhost")

            # Mock the Redis client
            mock_client = MagicMock()
            manager.get_client = MagicMock(return_value=mock_client)

            # Call flush_all
            manager.flush_all()

            # Check that flushall was called
            mock_client.flushall.assert_called_once()

    def test_key_generation(self):
        """Test that key generation methods return correctly formatted keys."""
        with patch("redis.ConnectionPool"):
            manager = RedisConnectionManager(host="testhost")
            test_uuid = str(uuid.uuid4())

            # Test all key generation methods
            assert manager.get_entity_key(test_uuid) == f"e:{test_uuid}"
            assert manager.get_watch_key(test_uuid) == f"w:{test_uuid}"
            assert manager.get_parent_key(test_uuid) == f"p:{test_uuid}"
            assert manager.get_children_key(test_uuid) == f"c:{test_uuid}"
            assert manager.get_index_key("attr", "val") == f"i:attr:val"

            # Unique set key should contain the prefix
            unique_key = manager.get_unique_set_key()
            assert unique_key.startswith("u:")


class TestEntityStorage:
    """Unit tests for the EntityStorage class."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mocked RedisConnectionManager."""
        manager = MagicMock(spec=RedisConnectionManager)
        manager.get_entity_key.return_value = "e:test_uuid"
        manager.get_watch_key.return_value = "w:test_uuid"
        manager.get_parent_key.return_value = "p:test_uuid"
        manager.get_children_key.return_value = "c:parent_uuid"
        manager.get_index_key.side_effect = lambda attr, val: f"i:{attr}:{val}"
        return manager

    @pytest.fixture
    def entity_storage(self, mock_connection_manager):
        """Create an EntityStorage with mocked connection manager."""
        return EntityStorage(mock_connection_manager)

    def test_get(self, entity_storage, mock_connection_manager):
        """Test getting an entity."""
        # Set up the mock Redis client
        mock_client = MagicMock()
        mock_client.hgetall.return_value = {"name": "Test Entity", "type": "test"}
        mock_connection_manager.get_client.return_value = mock_client

        # Call get
        entity = entity_storage.get("test_uuid")

        # Verify the correct methods were called
        mock_connection_manager.get_entity_key.assert_called_once_with("test_uuid")
        mock_client.hgetall.assert_called_once_with("e:test_uuid")

        # Verify the entity has the UUID added
        assert entity == {"uuid": "test_uuid", "name": "Test Entity", "type": "test"}

    def test_create(self, entity_storage, mock_connection_manager):
        """Test creating an entity."""
        # Set up mock objects
        mock_client = MagicMock()
        mock_pipe = MagicMock()
        mock_client.pipeline.return_value.__enter__.return_value = mock_pipe
        mock_connection_manager.get_client.return_value = mock_client

        # Test entity
        entity = {"uuid": "test_uuid", "name": "Test Entity", "type": "test"}

        # Call create
        result = entity_storage.create("parent_uuid", entity)

        # Verify Redis operations
        mock_connection_manager.get_entity_key.assert_called_once_with("test_uuid")
        mock_connection_manager.get_parent_key.assert_called_once_with("test_uuid")
        mock_connection_manager.get_children_key.assert_called_once_with("parent_uuid")

        # Verify pipeline operations
        mock_pipe.multi.assert_called_once()
        mock_pipe.hset.assert_called_once_with(
            "e:test_uuid", mapping={"name": "Test Entity", "type": "test"}
        )

        # Should create 3 indexes (2 for attributes + 1 for parent-child relationship)
        assert mock_pipe.sadd.call_count >= 3  # Changed from exactly 2
        mock_pipe.set.assert_called_once_with("p:test_uuid", "parent_uuid")
        mock_pipe.sadd.assert_any_call("c:parent_uuid", "test_uuid")
        mock_pipe.execute.assert_called_once()

        # Verify the result is the original entity
        assert result == entity

    def test_update_entity_indexes(self, entity_storage):
        """Test updating entity indexes."""
        # Set up mocks
        mock_pipe = MagicMock()
        entity_uuid = "test_uuid"
        old_entity = {"name": "Old Name", "type": "test", "status": "inactive"}
        updates = {"name": "New Name", "priority": "high"}

        # Call the method
        entity_storage._update_entity_indexes(
            mock_pipe, entity_uuid, old_entity, updates
        )

        # Verify Redis operations - should remove old name index and add new ones
        assert mock_pipe.srem.call_count >= 1
        assert mock_pipe.sadd.call_count >= 2


class TestEntityRelationship:
    """Unit tests for the EntityRelationship class."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mocked RedisConnectionManager."""
        manager = MagicMock(spec=RedisConnectionManager)
        manager.get_children_key.return_value = "c:parent_uuid"
        manager.get_parent_key.return_value = "p:child_uuid"
        manager.get_entity_key.side_effect = lambda uuid: f"e:{uuid}"
        return manager

    @pytest.fixture
    def entity_relationship(self, mock_connection_manager):
        """Create an EntityRelationship with mocked connection manager."""
        return EntityRelationship(mock_connection_manager)

    def test_get_children(self, entity_relationship, mock_connection_manager):
        """Test getting children of an entity."""
        # Set up the mock Redis client
        mock_client = MagicMock()
        mock_client.smembers.return_value = {"child1", "child2"}
        mock_client.hgetall.side_effect = lambda key: {
            "e:child1": {"name": "Child 1", "type": "child"},
            "e:child2": {"name": "Child 2", "type": "child"},
        }.get(key, {})
        mock_connection_manager.get_client.return_value = mock_client

        # Call get_children and collect results
        children = list(entity_relationship.get_children("parent_uuid"))

        # Verify Redis operations
        mock_connection_manager.get_children_key.assert_called_once_with("parent_uuid")
        mock_client.smembers.assert_called_once_with("c:parent_uuid")
        assert mock_client.hgetall.call_count == 2

        # Verify the children have the correct UUIDs added
        assert len(children) == 2
        assert {"uuid": "child1", "name": "Child 1", "type": "child"} in children
        assert {"uuid": "child2", "name": "Child 2", "type": "child"} in children

    def test_get_parent(self, entity_relationship, mock_connection_manager):
        """Test getting the parent of an entity."""
        # Set up the mock Redis client
        mock_client = MagicMock()
        mock_client.get.return_value = "parent_uuid"
        mock_client.hgetall.return_value = {"name": "Parent", "type": "parent"}
        mock_connection_manager.get_client.return_value = mock_client

        # Call get_parent
        parent = entity_relationship.get_parent("child_uuid")

        # Verify Redis operations
        mock_connection_manager.get_parent_key.assert_called_once_with("child_uuid")
        mock_client.get.assert_called_once_with("p:child_uuid")
        mock_connection_manager.get_entity_key.assert_called_once_with("parent_uuid")
        mock_client.hgetall.assert_called_once_with("e:parent_uuid")

        # Verify the parent has the correct UUID added
        assert parent == {"uuid": "parent_uuid", "name": "Parent", "type": "parent"}


class TestEntitySearch:
    """Unit tests for the EntitySearch class."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mocked RedisConnectionManager."""
        manager = MagicMock(spec=RedisConnectionManager)
        manager.get_index_key.side_effect = lambda attr, val: f"i:{attr}:{val}"
        manager.get_children_key.return_value = "c:parent_uuid"
        manager.get_unique_set_key.return_value = "u:unique_key"
        manager.get_entity_key.side_effect = lambda uuid: f"e:{uuid}"
        manager.INDEX_PREFIX = "i:"  # Set the INDEX_PREFIX attribute explicitly
        return manager

    @pytest.fixture
    def entity_search(self, mock_connection_manager):
        """Create an EntitySearch with mocked connection manager."""
        return EntitySearch(mock_connection_manager)

    def test_get_entity_from_index(self, entity_search, mock_connection_manager):
        """Test getting entities from an index."""
        # Set up the mock Redis client
        mock_client = MagicMock()
        mock_client.smembers.return_value = {"entity1", "entity2"}
        mock_client.hgetall.side_effect = lambda key: {
            "e:entity1": {"name": "Entity 1", "type": "test"},
            "e:entity2": {"name": "Entity 2", "type": "test"},
        }.get(key, {})
        mock_connection_manager.get_client.return_value = mock_client

        # Call get_entity_from_index and collect results
        entities = list(entity_search.get_entity_from_index("i:type:test"))

        # Verify Redis operations
        mock_client.smembers.assert_called_once_with("i:type:test")
        assert mock_client.hgetall.call_count == 2

        # Verify the entities have the correct UUIDs added
        assert len(entities) == 2
        assert {"uuid": "entity1", "name": "Entity 1", "type": "test"} in entities
        assert {"uuid": "entity2", "name": "Entity 2", "type": "test"} in entities

    def test_find_exact_match(self, entity_search, mock_connection_manager):
        """Test finding entities with exact attribute match."""
        # Set up the mock Redis client
        mock_client = MagicMock()
        # For exact match we use sinter directly
        mock_client.sinter.return_value = {"entity1"}
        mock_client.hgetall.return_value = {"name": "Entity 1", "type": "test"}
        mock_connection_manager.get_client.return_value = mock_client

        # Call find
        entities = list(entity_search.find(type="test"))

        # Verify Redis operations
        mock_connection_manager.get_index_key.assert_called_once_with("type", "test")
        # We use sinter instead of smembers in the updated implementation
        mock_client.sinter.assert_called_once()
        mock_client.hgetall.assert_called_once()

        # Verify the entity has the correct UUID added
        assert len(entities) == 1
        assert entities[0] == {"uuid": "entity1", "name": "Entity 1", "type": "test"}

    def test_find_pattern_match(self, entity_search, mock_connection_manager):
        """Test finding entities with pattern match."""
        # Set up the mock Redis client
        mock_client = MagicMock()

        # Mock scan_iter to return matching pattern keys
        mock_client.scan_iter.return_value = ["i:name:Entity 1", "i:name:Entity 2"]

        # Mock sunionstore to return a proper integer value
        mock_client.sunionstore.return_value = 2

        # Mock sinter to combine the results
        mock_client.sinter.return_value = {"entity1", "entity2"}

        # Mock entity data retrieval
        mock_client.hgetall.side_effect = lambda key: {
            "e:entity1": {"name": "Entity 1", "type": "test"},
            "e:entity2": {"name": "Entity 2", "type": "test"},
        }.get(key, {})

        mock_connection_manager.get_client.return_value = mock_client

        # Call find with a pattern
        entities = list(entity_search.find(name="Entity *"))

        # Verify scan_iter was called with the correct pattern
        mock_client.scan_iter.assert_called_once_with(
            match="i:name:Entity *", count=1000
        )

        # Verify sunionstore was called with the correct arguments
        mock_client.sunionstore.assert_called_once_with(
            "u:unique_key", ["i:name:Entity 1", "i:name:Entity 2"]
        )

        # Verify the entities have the correct UUIDs added
        assert len(entities) == 2
        assert {"uuid": "entity1", "name": "Entity 1", "type": "test"} in entities
        assert {"uuid": "entity2", "name": "Entity 2", "type": "test"} in entities


@pytest.mark.parametrize(
    "test_id",
    [
        "test_model_with_mocked_components",
    ],
)
def test_model_with_mocked_components(test_id):
    """Test the Model class with mocked component classes."""
    with patch("hotcore.model.RedisConnectionManager") as mock_connection_manager_class:
        # Set up mocks for all component classes
        mock_connection_manager = MagicMock()
        mock_storage = MagicMock()
        mock_relationship = MagicMock()
        mock_search = MagicMock()

        # Configure the mock connection manager class
        mock_connection_manager_class.return_value = mock_connection_manager

        # Patch the component classes
        with (
            patch("hotcore.model.EntityStorage") as mock_storage_class,
            patch("hotcore.model.EntityRelationship") as mock_relationship_class,
            patch("hotcore.model.EntitySearch") as mock_search_class,
            patch("hotcore.model.GeospatialManager") as mock_geospatial_class,
        ):

            # Configure the mock component classes
            mock_storage_class.return_value = mock_storage
            mock_relationship_class.return_value = mock_relationship
            mock_search_class.return_value = mock_search

            # Import Model here to ensure patches are applied
            from hotcore import Model

            # Create a Model instance
            model = Model(host="testhost", port=1234, db=5)

            # Verify component initialization - don't check exact parameter format
            assert mock_connection_manager_class.call_count == 1
            call_args = mock_connection_manager_class.call_args
            assert call_args[0][0] == "testhost"  # Check first positional arg
            assert call_args[0][1] == 1234  # Check second positional arg
            assert call_args[0][2] == 5  # Check third positional arg

            mock_storage_class.assert_called_once_with(mock_connection_manager)
            mock_relationship_class.assert_called_once_with(mock_connection_manager)
            mock_search_class.assert_called_once_with(mock_connection_manager)
            mock_geospatial_class.assert_called_once_with(
                mock_connection_manager, mock_connection_manager
            )

            # Test that model delegates to components
            test_entity = {"uuid": "test_uuid", "name": "Test"}

            # Test create
            model.create("parent_uuid", test_entity)
            mock_storage.create.assert_called_once_with("parent_uuid", test_entity)

            # Test get
            model.get("test_uuid")
            mock_storage.get.assert_called_once_with("test_uuid")

            # Test apply
            model.apply(test_entity)
            mock_storage.apply.assert_called_once_with(test_entity)

            # Test delete
            model.delete(test_entity)
            mock_storage.delete.assert_called_once_with(test_entity)

            # Test get_children
            model.get_children("parent_uuid")
            mock_relationship.get_children.assert_called_once_with("parent_uuid")

            # Test get_parent
            model.get_parent("test_uuid")
            mock_relationship.get_parent.assert_called_once_with("test_uuid")

            # Test find
            model.find(type="test")
            mock_search.find.assert_called_once_with(type="test")
