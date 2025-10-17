"""Test for setting up data needed by other real Redis tests."""

import logging

import pytest

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.DEBUG
)


@pytest.mark.redis_required
class TestDataSetup:
    """Tests for setting up data needed by other real Redis tests."""

    def test_setup_search_data(self, model):
        """Set up data needed for the advanced search tests."""
        # Create a parent entity
        parent = model.init({})
        parent["name"] = "parent_23"
        parent["type"] = "parent"
        model.create("root", parent)

        # Create multiple child entities with various attributes
        for i in range(100):
            entity = model.init({})
            entity["name"] = f"entity_{i}"
            entity["type"] = "child"
            entity["attribute_1"] = f"e_{i}_attribute_1"
            entity["attribute_2"] = f"e_{i}_attribute_2"
            entity["attribute_3"] = f"e_{i}_attribute_3"
            model.create(parent["uuid"], entity)

        # Verify data was created
        children = list(model.get_children(parent["uuid"]))
        assert len(children) == 100

        # Verify searchability
        attribute_1_search = list(model.find(attribute_1="e_42_attribute_1"))
        assert len(attribute_1_search) == 1
        assert attribute_1_search[0]["name"] == "entity_42"
