"""Performance tests for the Hotcore model with fakeredis."""

import logging
import time
from datetime import datetime

import pytest

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.DEBUG
)


class TestPerformance:
    """Performance tests for the Model class using fakeredis."""

    def test_load_small(self, model):
        """Test loading a smaller dataset for quick testing with fakeredis."""
        # Start timing
        start_time = datetime.now().timestamp()

        # Create a smaller dataset for fakeredis (5 parents, 10 children each, 10 attributes)
        for parent_cnt in range(1, 6):
            parent = model.init({})
            parent_uuid = parent["uuid"]
            parent["name"] = f"parent_{parent_cnt}"

            # Add attributes to parent
            for attribute_cnt in range(1, 11):
                parent[f"attribute_{attribute_cnt}"] = (
                    f"p_{parent_cnt}_attribute_{attribute_cnt}"
                )

            model.create("parent1", parent)

            # Create children for this parent
            for child_cnt in range(1, 11):
                entity = model.init({})
                entity["name"] = f"entity_{child_cnt}"

                # Add attributes to child
                for attribute_cnt in range(1, 11):
                    entity[f"attribute_{attribute_cnt}"] = (
                        f"e_{child_cnt}_attribute_{attribute_cnt}"
                    )

                model.create(parent_uuid, entity)

        # End timing
        end_time = datetime.now().timestamp()
        duration = end_time - start_time

        # Log performance
        logging.info(f"Small dataset creation completed in {duration:.6f} seconds")

        # Verify data was created
        all_parents = list(model.find(name="parent_*"))
        assert len(all_parents) == 5

        # Check that children were created for the first parent
        first_parent = next(
            parent for parent in all_parents if parent["name"] == "parent_1"
        )
        children = list(model.get_children(first_parent["uuid"]))
        assert len(children) == 10
