import time
from datetime import datetime
import unittest
from hotcore.model import Model


class ModelTestCase(unittest.TestCase):
    def test_search(self):
        model = Model('localhost')

        start_time = datetime.now().timestamp()
        print(list(model.find('attribute_1', 'p_8?_attribute_1')))
        print(list(model.get_entity_from_index('i:attribute_2:p_80_attribute_2')))
        for entity in model.get_children('parent1'):
            print(entity)
            break

        parent = model.get_parent(entity['uuid'])
        print('parent:' + str(parent))

        end_time = datetime.now().timestamp()
        print('Start:' + str(start_time))
        print('End  :' + str(end_time))
        print('Time:' + str((end_time - start_time) / 1.0))


if __name__ == '__main__':
    unittest.main()
