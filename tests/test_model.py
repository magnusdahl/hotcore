import unittest
from hotcore.model import Model


class ModelTestCase(unittest.TestCase):
    def test_operations(self):
        model = Model('localhost')
        model.flush_all()
        entity: dict = model.init({})
        entity_uuid = entity['uuid']
        entity["key1"] = "value1"
        entity["key2"] = "value2"
        model.create('parent1', entity)
        read_back = model.get(entity_uuid)
        self.assertTrue(entity == read_back, "Not matching")
        change: dict = {'uuid': entity['uuid'], 'key1': 'change1', 'key2': None, 'key3': 'new3'}
        model.apply(change)
        read_back = model.get(entity_uuid)
        print('Get parent:' + model.get_parent(read_back))
        hits = model.find('key*', '*')
        for entity in hits:
            print('Hit:')
            print(entity)
        for child in model.get_children({'uuid': 'parent1'}):
            print('Child:')
            print(child)

        model.delete(read_back)


if __name__ == '__main__':
    unittest.main()
