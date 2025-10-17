import logging
import time
import unittest
from datetime import datetime

from hotcore import Model

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.DEBUG
)


class ModelTestCase(unittest.TestCase):
    def test_load(self):
        model = Model("localhost")
        model.flush_all()

        start_time = datetime.now().timestamp()
        for parent_cnt in range(1, 100):
            parent: dict[str, str] = model.init({})
            parent_uuid = parent["uuid"]
            parent["name"] = "parent_" + str(parent_cnt)
            for attribute_cnt in range(1, 50):
                parent["attribute_" + str(attribute_cnt)] = (
                    "p_" + str(parent_cnt) + "_attribute_" + str(attribute_cnt)
                )
            model.create("parent1", parent)

            for child_cnt in range(1, 50):
                entity: dict[str, str] = model.init({})
                entity_uuid = entity["uuid"]
                entity["name"] = "entity_" + str(child_cnt)
                for attribute_cnt in range(1, 50):
                    entity["attribute_" + str(attribute_cnt)] = (
                        "e_" + str(child_cnt) + "_attribute_" + str(attribute_cnt)
                    )
                model.create(parent_uuid, entity)

        end_time = datetime.now().timestamp()
        print("Start:" + str(start_time))
        print("End  :" + str(end_time))
        print("Time:" + str((end_time - start_time) / 1.0))


if __name__ == "__main__":
    unittest.main()
