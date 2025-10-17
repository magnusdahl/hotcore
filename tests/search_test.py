import logging
import time
import unittest
from datetime import datetime

from hotcore import Model

logging.Formatter.converter = time.gmtime
logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.DEBUG
)


class ModelTestCase(unittest.TestCase):
    def test_search(self):
        model = Model("localhost")

        start_time = datetime.now().timestamp()
        parent = list(model.find(name="parent_23"))[0]
        # print("Wildcard search:" + str(list(model.find(parent=parent['uuid'], attribute_1='e_8?_attribute_1'))))
        print(
            "Multiple wildcard search:"
            + str(
                list(
                    model.find(
                        parent=parent["uuid"],
                        attribute_1="e_4?_attribute_1",
                        attribute_2="e_4?_attribute_2",
                    )
                )
            )
        )
        # print("Fixed value search:" + str(list(model.find(parent=parent['uuid'], attribute_1='e_87_attribute_1'))))

        end_time = datetime.now().timestamp()
        print("Start:" + str(start_time))
        print("End  :" + str(end_time))
        print("Time:" + str((end_time - start_time) / 1.0))


if __name__ == "__main__":
    unittest.main()
