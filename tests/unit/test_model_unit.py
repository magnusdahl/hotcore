import uuid

import pytest

from hotcore import Model


class TestModelUnit:
    """Unit tests for the Model class using fakeredis."""

    def test_model_init(self, model):
        """Test initializing an entity with the Model."""
        # Test initializing an entity
        entity = model.init({})
        assert "uuid" in entity
        assert isinstance(entity["uuid"], str)

        # Test initializing with existing data
        data = {"name": "Test Entity", "type": "test"}
        entity = model.init(data)
        assert "uuid" in entity
        assert entity["name"] == "Test Entity"
        assert entity["type"] == "test"

    def test_create_and_get(self, model):
        """Test creating and retrieving an entity."""
        # Create a test entity
        entity = model.init({})
        entity["name"] = "Test Entity"
        entity["type"] = "test"
        parent_uuid = "root"

        created = model.create(parent_uuid, entity)
        assert created["uuid"] == entity["uuid"]

        # Retrieve the entity
        retrieved = model.get(entity["uuid"])
        assert retrieved["uuid"] == entity["uuid"]
        assert retrieved["name"] == "Test Entity"
        assert retrieved["type"] == "test"

    def test_apply_changes(self, model):
        """Test applying changes to an entity."""
        # Create a test entity
        entity = model.init({})
        entity["name"] = "Original Name"
        entity["type"] = "test"
        entity["status"] = "active"
        parent_uuid = "root"

        model.create(parent_uuid, entity)

        # Apply changes
        changes = {
            "uuid": entity["uuid"],
            "name": "Updated Name",
            "status": None,  # Remove this attribute
            "priority": "high",  # Add this attribute
        }

        model.apply(changes)

        # Verify changes
        updated = model.get(entity["uuid"])
        assert updated["name"] == "Updated Name"
        assert "status" not in updated
        assert updated["priority"] == "high"
        assert updated["type"] == "test"  # Unchanged

    def test_delete(self, model):
        """Test deleting an entity."""
        # Create a test entity
        entity = model.init({})
        entity["name"] = "Entity to Delete"
        parent_uuid = "root"

        model.create(parent_uuid, entity)

        # Verify entity exists
        retrieved = model.get(entity["uuid"])
        assert retrieved["uuid"] == entity["uuid"]

        # Delete the entity
        model.delete(entity)

        # Verify entity no longer exists
        empty_entity = model.get(entity["uuid"])
        assert empty_entity == {"uuid": entity["uuid"]}

    def test_parent_child_relationship(self, model):
        """Test parent-child relationships."""
        # Create a parent
        parent = model.init({})
        parent["name"] = "Parent Entity"
        parent["type"] = "parent"
        model.create("root", parent)

        # Create child entities
        child1 = model.init({})
        child1["name"] = "Child 1"
        child1["type"] = "child"
        model.create(parent["uuid"], child1)

        child2 = model.init({})
        child2["name"] = "Child 2"
        child2["type"] = "child"
        model.create(parent["uuid"], child2)

        # Test getting parent
        retrieved_parent = model.get_parent(child1["uuid"])
        assert retrieved_parent["uuid"] == parent["uuid"]

        # Test getting children
        children = list(model.get_children(parent["uuid"]))
        assert len(children) == 2
        child_uuids = [child["uuid"] for child in children]
        assert child1["uuid"] in child_uuids
        assert child2["uuid"] in child_uuids

    def test_find(self, model):
        """Test finding entities by attributes."""
        # Create test entities
        parent = model.init({})
        parent["name"] = "Test Parent"
        parent["type"] = "parent"
        model.create("root", parent)

        # Create multiple child entities
        for i in range(5):
            child = model.init({})
            child["name"] = f"Child {i}"
            child["type"] = "child"
            child["status"] = "active" if i % 2 == 0 else "inactive"
            child["priority"] = "high" if i < 2 else "low"
            model.create(parent["uuid"], child)

        # Find by exact match
        active_children = list(model.find(type="child", status="active"))
        assert len(active_children) == 3  # 0, 2, 4 are active

        # Find with wildcard
        child_0 = list(model.find(name="Child 0"))
        assert len(child_0) == 1
        assert child_0[0]["name"] == "Child 0"

        # Find with pattern
        children = list(model.find(name="Child *"))
        assert len(children) == 5

        # Find with multiple criteria
        high_active = list(model.find(type="child", status="active", priority="high"))
        assert len(high_active) == 1  # Only Child 0 is both active and high priority
