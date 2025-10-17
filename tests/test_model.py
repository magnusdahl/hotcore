import logging
import unittest

from hotcore import Model

logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.DEBUG
)


class ModelTestCase(unittest.TestCase):
    def test_example(self):
        # Create a department
        model = Model("localhost")
        # Clean full dataset
        model.flush_all()

        group1: dict[str, str] = model.init({})
        group1["type"] = "dept"
        group1["name"] = "First Dept"
        group1["address1"] = "First Street 2"
        group1["address2"] = "12345 City"
        group1["zip"] = "12345"
        model.create("root1", group1)

        # Create two employees
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
        print(
            "Li*:"
            + str(
                list(model.find(parent=group1["uuid"], type="employee", name="[Ll]i*"))
            )
        )
        print("Children:" + str(list(model.find(parent=group1["uuid"]))))

    def test_operations(self):
        model = Model("localhost")
        model.flush_all()
        entity: dict = model.init({})
        entity_uuid = entity["uuid"]
        entity["key1"] = "value1"
        entity["key2"] = "value2"
        model.create("parent1", entity)
        read_back = model.get(entity_uuid)
        self.assertTrue(entity == read_back, "Not matching")
        change: dict = {
            "uuid": entity["uuid"],
            "key1": "change1",
            "key2": None,
            "key3": "new3",
        }
        model.apply(change)
        read_back = model.get(entity_uuid)
        print("Get parent:" + str(model.get_parent(entity_uuid)))
        for child in model.get_children("parent1"):
            print("Child:")
            print(child)

        model.delete(read_back)


if __name__ == "__main__":
    unittest.main()
