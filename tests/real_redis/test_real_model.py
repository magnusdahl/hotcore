"""Tests that require a real Redis server.

These tests are marked with pytest.mark.redis_required and will be
skipped if USE_REAL_REDIS is not set to true.
"""

import logging

import pytest

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.DEBUG
)


@pytest.mark.redis_required
class TestRealRedisModel:
    """Tests that require a real Redis server."""

    def test_example(self, model):
        """Test creating a department and employees and find employees by name pattern."""
        # Create a department
        group1 = model.init({})
        group1["type"] = "dept"
        group1["name"] = "First Dept"
        group1["address1"] = "First Street 2"
        group1["address2"] = "12345 City"
        group1["zip"] = "12345"
        model.create("root1", group1)

        # Create three employees
        employee1 = model.init({})
        employee1["type"] = "employee"
        employee1["name"] = "Bart"
        employee1["address1"] = "Second Street 1"
        employee1["address2"] = "12344 Other City"
        employee1["zip"] = "12344"
        model.create(group1["uuid"], employee1)

        employee2 = model.init({})
        employee2["type"] = "employee"
        employee2["name"] = "Lisa"
        employee2["address1"] = "Second Street 1"
        employee2["address2"] = "12344 Other City"
        employee2["zip"] = "12344"
        model.create(group1["uuid"], employee2)

        employee3 = model.init({})
        employee3["type"] = "employee"
        employee3["name"] = "Linda"
        employee3["address1"] = "Third Street 3"
        employee3["address2"] = "12343 Other City"
        employee3["zip"] = "12343"
        model.create(group1["uuid"], employee3)

        # Find an employee with a name staring with li
        li_employees = list(
            model.find(parent=group1["uuid"], type="employee", name="[Ll]i*")
        )
        assert len(li_employees) == 2  # Should find Lisa and Linda

        # Get all children
        children = list(model.find(parent=group1["uuid"]))
        assert len(children) == 3  # Should find all three employees

    def test_operations(self, model):
        """Test basic CRUD operations."""
        entity = model.init({})
        entity_uuid = entity["uuid"]
        entity["key1"] = "value1"
        entity["key2"] = "value2"
        model.create("parent1", entity)

        # Verify retrieval
        read_back = model.get(entity_uuid)
        assert entity == read_back

        # Test applying changes
        change = {
            "uuid": entity["uuid"],
            "key1": "change1",
            "key2": None,
            "key3": "new3",
        }
        model.apply(change)

        # Verify changes
        read_back = model.get(entity_uuid)
        assert read_back["key1"] == "change1"
        assert "key2" not in read_back
        assert read_back["key3"] == "new3"

        # Test parent-child relationship
        parent = model.get_parent(entity_uuid)
        assert parent["uuid"] == "parent1"

        children = list(model.get_children("parent1"))
        assert len(children) == 1
        assert children[0]["uuid"] == entity_uuid

        # Test deletion
        model.delete(read_back)

        # Verify entity is gone
        empty_entity = model.get(entity_uuid)
        assert empty_entity == {"uuid": entity_uuid}
