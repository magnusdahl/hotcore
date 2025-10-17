"""Unit tests for error handling and edge cases in Model class and components.

These tests focus on error conditions, edge cases, and exception handling to ensure
the Model and its components are robust under unusual circumstances.
"""

from unittest.mock import MagicMock, patch

import pytest
import redis

from hotcore import (
    EntityRelationship,
    EntitySearch,
    EntityStorage,
    Model,
    RedisConnectionManager,
)


class TestRedisConnectionManagerErrors:
    """Tests for error handling in RedisConnectionManager."""

    def test_redis_error_in_flush_all(self):
        """Test handling of Redis errors in flush_all method."""
        with patch("redis.ConnectionPool"):
            manager = RedisConnectionManager(host="testhost")

            # Mock Redis client to raise an exception
            mock_client = MagicMock()
            mock_client.flushall.side_effect = redis.RedisError("Test Redis error")
            manager.get_client = MagicMock(return_value=mock_client)

            # Verify that the exception is re-raised
            with pytest.raises(redis.RedisError) as excinfo:
                manager.flush_all()

            assert "Test Redis error" in str(excinfo.value)


class TestEntityStorageErrors:
    """Tests for error handling in EntityStorage."""

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

    def test_get_with_redis_error(self, entity_storage, mock_connection_manager):
        """Test handling of Redis errors in get method."""
        # Set up the mock Redis client to raise an exception
        mock_client = MagicMock()
        mock_client.hgetall.side_effect = redis.RedisError("Test Redis error")
        mock_connection_manager.get_client.return_value = mock_client

        # Verify that the exception is re-raised
        with pytest.raises(redis.RedisError) as excinfo:
            entity_storage.get("test_uuid")

        assert "Test Redis error" in str(excinfo.value)

    def test_create_with_missing_uuid(self, entity_storage):
        """Test create with entity missing UUID."""
        # Entity without UUID
        entity = {"name": "Test Entity", "type": "test"}

        # Verify that TypeError is raised
        with pytest.raises(TypeError) as excinfo:
            entity_storage.create("parent_uuid", entity)

        assert "uuid" in str(excinfo.value).lower()

    def test_create_with_redis_error(self, entity_storage, mock_connection_manager):
        """Test handling of Redis errors in create method."""
        # Set up mock objects
        mock_client = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.side_effect = redis.RedisError("Test Redis error")
        mock_client.pipeline.return_value.__enter__.return_value = mock_pipe
        mock_connection_manager.get_client.return_value = mock_client

        # Test entity
        entity = {"uuid": "test_uuid", "name": "Test Entity", "type": "test"}

        # Verify that the exception is re-raised
        with pytest.raises(redis.RedisError) as excinfo:
            entity_storage.create("parent_uuid", entity)

        assert "Test Redis error" in str(excinfo.value)

    def test_apply_with_watch_error(self, entity_storage, mock_connection_manager):
        """Test handling of watch errors in apply method."""
        # Set up mock objects
        mock_client = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.side_effect = redis.WatchError("Watch failed")
        mock_client.pipeline.return_value.__enter__.return_value = mock_pipe
        mock_connection_manager.get_client.return_value = mock_client

        # Test entity changes
        changes = {"uuid": "test_uuid", "name": "Updated Name"}

        # Should log the error and try again, but eventually fail after max retries
        with pytest.raises(redis.WatchError) as excinfo:
            entity_storage.apply(changes)

        assert "Watch failed" in str(excinfo.value)


class TestEntityRelationshipErrors:
    """Tests for error handling in EntityRelationship."""

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

    def test_get_children_with_redis_error(
        self, entity_relationship, mock_connection_manager
    ):
        """Test handling of Redis errors in get_children method."""
        # Set up the mock Redis client to raise an exception
        mock_client = MagicMock()
        mock_client.smembers.side_effect = redis.RedisError("Test Redis error")
        mock_connection_manager.get_client.return_value = mock_client

        # Verify that the exception is re-raised
        with pytest.raises(redis.RedisError) as excinfo:
            list(entity_relationship.get_children("parent_uuid"))

        assert "Test Redis error" in str(excinfo.value)

    def test_get_parent_with_redis_error(
        self, entity_relationship, mock_connection_manager
    ):
        """Test handling of Redis errors in get_parent method."""
        # Set up the mock Redis client to raise an exception
        mock_client = MagicMock()
        mock_client.get.side_effect = redis.RedisError("Test Redis error")
        mock_connection_manager.get_client.return_value = mock_client

        # Verify that the exception is re-raised
        with pytest.raises(redis.RedisError) as excinfo:
            entity_relationship.get_parent("child_uuid")

        assert "Test Redis error" in str(excinfo.value)

    def test_get_parent_with_nonexistent_parent(
        self, entity_relationship, mock_connection_manager
    ):
        """Test get_parent with nonexistent parent."""
        # Set up the mock Redis client to return None for the parent pointer
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_connection_manager.get_client.return_value = mock_client

        # Should return a "not found" entity with the root UUID
        parent = entity_relationship.get_parent("child_uuid")
        assert parent == {"uuid": "root"}


class TestEntitySearchErrors:
    """Tests for error handling in EntitySearch."""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mocked RedisConnectionManager."""
        manager = MagicMock(spec=RedisConnectionManager)
        manager.get_index_key.side_effect = lambda attr, val: f"i:{attr}:{val}"
        manager.get_children_key.return_value = "c:parent_uuid"
        manager.get_unique_set_key.return_value = "u:unique_key"
        manager.get_entity_key.side_effect = lambda uuid: f"e:{uuid}"
        return manager

    @pytest.fixture
    def entity_search(self, mock_connection_manager):
        """Create an EntitySearch with mocked connection manager."""
        return EntitySearch(mock_connection_manager)

    def test_get_entity_from_index_with_redis_error(
        self, entity_search, mock_connection_manager
    ):
        """Test handling of Redis errors in get_entity_from_index method."""
        # Set up the mock Redis client to raise an exception
        mock_client = MagicMock()
        mock_client.smembers.side_effect = redis.RedisError("Test Redis error")
        mock_connection_manager.get_client.return_value = mock_client

        # Verify that the exception is re-raised
        with pytest.raises(redis.RedisError) as excinfo:
            list(entity_search.get_entity_from_index("i:type:test"))

        assert "Test Redis error" in str(excinfo.value)

    def test_find_with_invalid_pattern(self, entity_search, mock_connection_manager):
        """Test find with invalid pattern that causes Redis error."""
        # Set up the mock Redis client to raise an exception for scan_iter
        mock_client = MagicMock()
        mock_client.scan_iter.side_effect = redis.RedisError("Invalid pattern")
        mock_connection_manager.get_client.return_value = mock_client

        # In our improved implementation, find() now handles Redis errors for patterns internally
        # by returning an empty result set, so we should just get an empty list back
        results = list(entity_search.find(name="[Invalid pattern"))
        assert len(results) == 0

        # We should still have attempted to scan with the pattern
        mock_client.scan_iter.assert_called_once()

        # And we should have logged the error
        # (can't easily test this with mocks, but we can ensure the code path is exercised)

    def test_find_with_empty_result(self, entity_search, mock_connection_manager):
        """Test find with no matching entities."""
        # Set up the mock Redis client to return empty results
        mock_client = MagicMock()
        mock_client.smembers.return_value = set()
        mock_client.keys.return_value = []
        mock_connection_manager.get_client.return_value = mock_client

        # Should return an empty list
        results = list(entity_search.find(type="nonexistent"))
        assert len(results) == 0


class TestModelErrors:
    """Tests for error handling in Model class."""

    @pytest.fixture
    def mock_components(self):
        """Create mocked components for Model."""
        connection = MagicMock(spec=RedisConnectionManager)
        storage = MagicMock(spec=EntityStorage)
        relationship = MagicMock(spec=EntityRelationship)
        search = MagicMock(spec=EntitySearch)

        # Configure component behavior
        storage.get.side_effect = lambda uuid: {"uuid": uuid, "name": "Test Entity"}

        return {
            "connection": connection,
            "storage": storage,
            "relationship": relationship,
            "search": search,
        }

    @pytest.fixture
    def model(self, mock_components):
        """Create a Model with mocked components."""
        # Create Model without calling __init__
        model_instance = Model.__new__(Model)

        # Set up components
        model_instance.connection = mock_components["connection"]
        model_instance.write_connection = mock_components["connection"]
        model_instance.storage = mock_components["storage"]
        model_instance.relationship = mock_components["relationship"]
        model_instance.search = mock_components["search"]
        model_instance.geospatial = MagicMock()

        # Set h3_index to None for error handling tests (H3 functionality not needed)
        model_instance.h3_index = None

        # Set up logger
        import logging

        model_instance.logger = logging.getLogger(__name__)

        return model_instance

    def test_init_with_none_entity(self, model):
        """Test init with None entity."""
        # Verify behavior with None input
        result = Model.init(None)
        assert isinstance(result, dict)
        assert "uuid" in result

    def test_create_with_component_error(self, model, mock_components):
        """Test handling of component errors in create method."""
        # Configure the storage component to raise an exception
        mock_components["storage"].create.side_effect = redis.RedisError(
            "Test Redis error"
        )

        # Test entity
        entity = {"uuid": "test_uuid", "name": "Test Entity"}

        # Verify that the exception is re-raised
        with pytest.raises(redis.RedisError) as excinfo:
            model.create("parent_uuid", entity)

        assert "Test Redis error" in str(excinfo.value)

    def test_complex_edge_case(self, model, mock_components):
        """Test a complex edge case involving multiple components."""
        # Configure component behavior for this test
        mock_components["relationship"].get_children.return_value = [
            {"uuid": "child1", "name": "Child 1"},
            {"uuid": "child2", "name": "Child 2"},
        ]

        mock_components["search"].find.side_effect = redis.RedisError("Search error")

        # Should be able to get children even if search fails
        children = list(model.get_children("parent_uuid"))
        assert len(children) == 2

        # But find should propagate the error
        with pytest.raises(redis.RedisError) as excinfo:
            list(model.find(type="test"))

        assert "Search error" in str(excinfo.value)
