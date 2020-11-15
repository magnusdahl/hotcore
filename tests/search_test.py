import time
from datetime import datetime
import unittest
from hotcore.model import Model


class ModelTestCase(unittest.TestCase):
    def test_search(self):
        model = Model('localhost')

        start_time = datetime.now().timestamp()
        parent = list(model.find(name='parent_2'))[0]
        #print("Li*:" + str(list(model.find(parent=parent['uuid'], attribute_1='e_8?_attribute_1'))))
        print("Li*:" + str(list(model.find(parent=parent['uuid'], attribute_1='e_87_attribute_1'))))

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
