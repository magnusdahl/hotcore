"""Unit tests for the Model.init static method.

These tests focus on the behavior and edge cases of the Model.init static method,
which was identified in TASKS.md as needing review and possible refactoring.
"""

import uuid

import pytest

from hotcore import Model


class TestModelInitMethod:
    """Tests for the Model.init static method."""

    def test_init_empty_dict(self):
        """Test initializing an entity with an empty dictionary."""
        entity = Model.init({})

        # Should create a dictionary with a UUID
        assert isinstance(entity, dict)
        assert "uuid" in entity
        assert isinstance(entity["uuid"], str)

        # UUID should be a valid UUID string
        uuid_obj = uuid.UUID(entity["uuid"])
        assert str(uuid_obj) == entity["uuid"]

    def test_init_with_existing_data(self):
        """Test initializing an entity with existing data."""
        original_data = {
            "name": "Test Entity",
            "type": "test_type",
            "attributes": {"key1": "value1", "key2": "value2"},
        }

        entity = Model.init(original_data)

        # Should add a UUID and preserve all original data
        assert "uuid" in entity
        assert entity["name"] == "Test Entity"
        assert entity["type"] == "test_type"
        assert entity["attributes"]["key1"] == "value1"
        assert entity["attributes"]["key2"] == "value2"

    def test_init_with_none(self):
        """Test initializing an entity with None."""
        entity = Model.init(None)

        # Should create a dictionary with a UUID
        assert isinstance(entity, dict)
        assert "uuid" in entity
        assert isinstance(entity["uuid"], str)

    def test_init_with_existing_uuid(self):
        """Test initializing an entity that already has a UUID."""
        existing_uuid = str(uuid.uuid4())
        original_data = {"uuid": existing_uuid, "name": "Test Entity"}

        entity = Model.init(original_data)

        # Should preserve the existing UUID
        assert entity["uuid"] == existing_uuid
        assert entity["name"] == "Test Entity"

    def test_init_with_non_string_uuid(self):
        """Test initializing an entity with a non-string UUID."""
        # Create a UUID object instead of a string
        uuid_obj = uuid.uuid4()
        original_data = {
            "uuid": uuid_obj,  # UUID object, not string
            "name": "Test Entity",
        }

        entity = Model.init(original_data)

        # Should convert the UUID to a string
        assert isinstance(entity["uuid"], str)
        assert entity["uuid"] == str(uuid_obj)

    @pytest.mark.parametrize(
        "input_data",
        [
            123,  # Integer
            "just a string",  # String
            ["item1", "item2"],  # List
            (1, 2, 3),  # Tuple
            set([1, 2, 3]),  # Set
        ],
    )
    def test_init_with_non_dict_input(self, input_data):
        """Test initializing an entity with non-dictionary input."""
        # Should convert to a dictionary and add a UUID
        entity = Model.init(input_data)

        assert isinstance(entity, dict)
        assert "uuid" in entity
        assert isinstance(entity["uuid"], str)

    def test_init_immutability(self):
        """Test that Model.init doesn't mutate the original data."""
        original_data = {"name": "Test Entity", "type": "test_type"}

        # Make a deep copy of the original data for comparison
        import copy

        original_copy = copy.deepcopy(original_data)

        # Initialize an entity with the original data
        entity = Model.init(original_data)

        # Verify that original_data is unchanged
        assert original_data == original_copy
        assert "uuid" not in original_data

    def test_init_uuid_generation_uniqueness(self):
        """Test that Model.init generates unique UUIDs for each call."""
        entity1 = Model.init({})
        entity2 = Model.init({})
        entity3 = Model.init({})

        # All UUIDs should be different
        assert entity1["uuid"] != entity2["uuid"]
        assert entity1["uuid"] != entity3["uuid"]
        assert entity2["uuid"] != entity3["uuid"]


class TestModelInitUsage:
    """Tests demonstrating the usage patterns of Model.init in the application."""

    def test_init_with_create(self, model):
        """Test initializing an entity and then creating it."""
        # Initialize a new entity
        entity = Model.init({})
        entity["name"] = "Test Entity"
        entity["type"] = "test_type"

        # Create the entity
        created = model.create("root", entity)

        # Verify the entity was created with the same UUID
        assert created["uuid"] == entity["uuid"]

        # Retrieve the entity
        retrieved = model.get(entity["uuid"])

        # Verify it matches the created entity
        assert retrieved["uuid"] == entity["uuid"]
        assert retrieved["name"] == "Test Entity"
        assert retrieved["type"] == "test_type"

    def test_init_with_multiple_entities(self, model):
        """Test initializing and creating multiple related entities."""
        # Create a parent entity
        parent = Model.init({})
        parent["name"] = "Parent Entity"
        parent["type"] = "parent"
        model.create("root", parent)

        # Create child entities
        children = []
        for i in range(3):
            child = Model.init({})
            child["name"] = f"Child {i}"
            child["type"] = "child"
            child["index"] = i
            model.create(parent["uuid"], child)
            children.append(child)

        # Verify parent-child relationships
        parent_children = list(model.get_children(parent["uuid"]))
        assert len(parent_children) == 3

        # Verify each child's parent is the parent we created
        for child in children:
            child_parent = model.get_parent(child["uuid"])
            assert child_parent["uuid"] == parent["uuid"]

    def test_init_purpose_analysis(self, model):
        """Analyze the purpose of Model.init in relation to Model.create."""
        # Initialize an entity without using Model.init
        entity = {"uuid": str(uuid.uuid4()), "name": "Manual Entity", "type": "test"}

        # Create the entity
        created = model.create("root", entity)

        # Verify the entity was created correctly
        assert created["uuid"] == entity["uuid"]

        # Retrieve the entity
        retrieved = model.get(entity["uuid"])

        # Verify it matches the created entity
        assert retrieved["uuid"] == entity["uuid"]
        assert retrieved["name"] == "Manual Entity"

        # This test demonstrates that Model.init is not strictly necessary
        # if you're willing to manually generate UUIDs. Its main purpose is
        # convenience - generating UUIDs and preparing entity dictionaries.
