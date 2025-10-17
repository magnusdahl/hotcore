"""Tests for search patterns with fakeredis."""

import logging
import time
from datetime import datetime

import pytest

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.DEBUG
)


class TestSearchPatterns:
    """Tests for search pattern functionality using fakeredis."""

    def test_search_setup(self, model):
        """Set up data and test search patterns."""
        # Create a parent entity
        parent = model.init({})
        parent["name"] = "parent_23"
        parent["type"] = "parent"
        model.create("root", parent)

        # Create entities with predictable attribute patterns
        for i in range(100):
            entity = model.init({})
            entity["name"] = f"entity_{i}"
            entity["type"] = "test_entity"
            entity["attribute_1"] = f"e_{i}_attribute_1"
            entity["attribute_2"] = f"e_{i}_attribute_2"
            entity["attribute_3"] = f"e_{i}_attribute_3"
            # Create some special entities to search for
            if i % 10 == 0:
                entity["tag"] = "special"
            model.create(parent["uuid"], entity)

        # Verify the setup
        all_entities = list(model.get_children(parent["uuid"]))
        assert len(all_entities) == 100

        # Test various search patterns

        # 1. Test exact match
        exact_match = list(model.find(attribute_1="e_42_attribute_1"))
        assert len(exact_match) == 1
        assert exact_match[0]["name"] == "entity_42"

        # 2. Test wildcard pattern
        pattern_match = list(model.find(attribute_1="e_4*_attribute_1"))
        assert len(pattern_match) >= 10  # Should find e_40 through e_49

        # 3. Test multiple criteria
        multi_criteria = list(model.find(type="test_entity", tag="special"))
        assert len(multi_criteria) == 10  # Should find the "special" entities

        # 4. Test parent constraint
        parent_constraint = list(
            model.find(parent=parent["uuid"], attribute_2="e_15_attribute_2")
        )
        assert len(parent_constraint) == 1
        assert parent_constraint[0]["name"] == "entity_15"

        # 5. Test combination of patterns
        combination = list(
            model.find(
                parent=parent["uuid"],
                attribute_1="e_5[0-9]_attribute_1",
                attribute_2="e_5[0-9]_attribute_2",
            )
        )
        assert len(combination) == 10  # Should find entities 50-59

        # Time a complex search to evaluate performance
        start_time = datetime.now().timestamp()

        # Perform a complex search
        results = list(
            model.find(
                parent=parent["uuid"],
                attribute_1="e_4?_attribute_1",
                attribute_2="e_4?_attribute_2",
            )
        )

        end_time = datetime.now().timestamp()
        duration = end_time - start_time

        # Log performance
        logging.info(
            f"Complex search found {len(results)} results in {duration:.6f} seconds"
        )
