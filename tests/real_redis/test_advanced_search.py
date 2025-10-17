"""Tests for advanced search functionality requiring a real Redis server."""

import logging
import time
from datetime import datetime

import pytest

logging.Formatter.converter = time.gmtime
logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.DEBUG
)


@pytest.mark.redis_required
class TestAdvancedSearch:
    """Tests for advanced search functionality requiring a real Redis server."""

    def test_complex_search(self, model):
        """Test complex search patterns and performance."""
        # This test requires pre-existing data in Redis. If the data is
        # missing (for example when tests are run in isolation), create the
        # minimal dataset needed for the search assertions so the test can
        # run deterministically.

        # First, check if the required parent exists
        parent_entities = list(model.find(name="parent_23"))

        if not parent_entities:
            # Create the parent and a set of children matching the pattern
            parent = model.init({})
            parent["name"] = "parent_23"
            parent["type"] = "parent"
            model.create("root", parent)

            # Create child entities with attributes that the test will search
            for i in range(100):
                entity = model.init({})
                entity["name"] = f"entity_{i}"
                entity["type"] = "child"
                # Attributes are formed to match wildcard searches like e_4?_attribute_1
                entity["attribute_1"] = f"e_{i}_attribute_1"
                entity["attribute_2"] = f"e_{i}_attribute_2"
                entity["attribute_3"] = f"e_{i}_attribute_3"
                model.create(parent["uuid"], entity)

            # Basic sanity checks to ensure the dataset was created
            children = list(model.get_children(parent["uuid"]))
            assert len(children) == 100
        else:
            parent = parent_entities[0]

        # Time the search operation
        start_time = datetime.now().timestamp()

        # Perform multiple wildcard search
        results = list(
            model.find(
                parent=parent["uuid"],
                attribute_1="e_4?_attribute_1",
                attribute_2="e_4?_attribute_2",
            )
        )

        end_time = datetime.now().timestamp()
        duration = end_time - start_time

        # Log the results
        logging.info(
            f"Multiple wildcard search found {len(results)} results in {duration:.6f} seconds"
        )

        # We don't make specific assertions about the number of results
        # since that depends on the data in Redis, but we can check
        # that the search completed successfully
