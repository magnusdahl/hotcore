import pytest

from hotcore import RedisConnectionManager


class TestRedisConnectionManager:
    """Unit tests for the RedisConnectionManager class."""

    def test_key_generation(self, redis_connection_manager):
        """Test that Redis keys are correctly generated."""
        manager = redis_connection_manager

        # Test entity key
        entity_uuid = "test-uuid"
        entity_key = manager.get_entity_key(entity_uuid)
        assert entity_key == f"{manager.ENTITY_PREFIX}{entity_uuid}"

        # Test watch key
        watch_key = manager.get_watch_key(entity_uuid)
        assert watch_key == f"{manager.WATCH_LOCK_PREFIX}{entity_uuid}"

        # Test parent key
        parent_key = manager.get_parent_key(entity_uuid)
        assert parent_key == f"{manager.PARENT_PREFIX}{entity_uuid}"

        # Test children key
        children_key = manager.get_children_key(entity_uuid)
        assert children_key == f"{manager.CHILDREN_PREFIX}{entity_uuid}"

        # Test index key
        attribute = "name"
        value = "test-name"
        index_key = manager.get_index_key(attribute, value)
        assert index_key == f"{manager.INDEX_PREFIX}{attribute}:{value}"

        # Test unique set key
        unique_key = manager.get_unique_set_key()
        assert unique_key.startswith(manager.FIND_UNIQUE_PREFIX)

    def test_client_connection(self, redis_connection_manager):
        """Test that Redis client connection works."""
        # Get a Redis client from the connection manager
        client = redis_connection_manager.get_client()

        # Test basic operations
        key = "test-key"
        value = "test-value"

        # Set a value
        client.set(key, value)

        # Get the value
        retrieved = client.get(key)
        assert retrieved == value

        # Clean up
        client.delete(key)

    def test_flush_all(self, redis_connection_manager):
        """Test flushing all keys."""
        client = redis_connection_manager.get_client()

        # Set some keys
        client.set("test-key-1", "value1")
        client.set("test-key-2", "value2")

        # Verify they exist
        assert client.get("test-key-1") == "value1"
        assert client.get("test-key-2") == "value2"

        # Flush all keys
        redis_connection_manager.flush_all()

        # Verify they no longer exist
        assert client.get("test-key-1") is None
        assert client.get("test-key-2") is None
