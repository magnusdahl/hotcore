""" Entity model for the core dataset of an application. The structural, referential, ever changing dataset

This module will manage a dataset in Redis with a tree structure

  Typical usage example:

  entity: dict = dict()
  bar = foo.FunctionBar()
"""
import logging
import uuid
import redis
from redis import WatchError


class Model:
    logger = logging.getLogger(__name__)
    _redisClient: redis.client = redis.Redis('localhost', port=6379, db=0, encoding='utf-8', decode_responses=True)

    def __init__(self, host: str):
        _redisClient = redis.Redis(host, port=6379, db=0, encoding='utf-8', decode_responses=True)

    def flush_all(self):
        self._redisClient.flushall()

    @staticmethod
    def init(entity: dict):
        entity.__setitem__('uuid', str(uuid.uuid4()))
        return entity

    def create(self, parent_uuid: str, entity: dict):
        """Create and save a new entity into the structure.

         Saving the entity and updating the parent to reflect the added child

         Args:
             parent_uuid: The uuid of the parent of this entity.
             entity: : A dictionary that contains the properties of the entity

         Raises:
             TypeError: An error occurred accessing the uuid of the entity.
         """
        with self._redisClient.pipeline() as pipe:
            pipe.multi()
            entity_uuid = entity['uuid']
            if entity_uuid is None:
                raise TypeError('entity must be a dictionary (dict) containing the key \'uuid\'')
            # Save the entity without the uuid value (temporary removed)
            del entity['uuid']
            pipe.hset('e:' + entity_uuid, mapping=entity)
            for key, value in entity.items():
                pipe.sadd('i:' + key + ':' + value, entity_uuid)
            entity['uuid'] = entity_uuid
            # Save the parent pointer
            pipe.set('p:' + entity_uuid, parent_uuid)
            # Reinstate the uuid value in the entity
            # Add this entity into the child list of the parent
            pipe.sadd('c:' + parent_uuid, entity_uuid)
            pipe.execute()
            return entity

    ##
    # Retrieve the entity for the given uuid
    # get.
    # @param entity_uuid The uuid of the entity to get.
    # @return The entity in form of a @dict

    def get(self, entity_uuid: str):
        entity_key = 'e:' + entity_uuid
        entity: dict = self._redisClient.hgetall(entity_key)
        entity['uuid'] = entity_uuid
        print('Get:' + str(entity))
        return entity

    ##
    # Save a change that can consist of new, updated or deleted entries
    # apply.
    # @return An integer value.

    def apply(self, change: dict):
        entity_uuid: str = change['uuid']
        watch_key = 'w:' + entity_uuid
        entity_key = 'e:' + entity_uuid
        with self._redisClient.pipeline() as pipe:
            while True:
                try:
                    # put a WATCH on the entity key (with a prefix because hash keys are not watchable)
                    pipe.watch(watch_key)
                    old_entity = pipe.hgetall(entity_key)
                    print(old_entity)
                    # now we can put the pipeline back into buffered mode with MULTI
                    pipe.multi()
                    pipe.set(watch_key, '')

                    updated_values: dict = dict(filter(lambda elem: elem[1] is not None and elem[0] != 'uuid', change.items()))
                    print(updated_values)
                    for key, value in change.items():
                        if value is None:
                            old_value = old_entity[key]
                            pipe.hdel(entity_key, key)
                            pipe.srem('i:' + key + ":" + old_value, entity_uuid)

                    if len(updated_values) > 0:
                        pipe.hset(entity_key, mapping=updated_values)
                        for key, value in updated_values.items():
                            if key in old_entity:
                                old_value = old_entity[key]
                                if old_value is not None:
                                    pipe.srem('i:' + key + ':' + old_value, entity_uuid)
                            pipe.sadd('i:' + key + ':' + value, entity_uuid)

                    # and finally, execute the pipeline (the set command)
                    pipe.execute()
                    break
                except WatchError:
                    # another client must have changed the entity between
                    # the time we started WATCHing it and the pipeline's execution.
                    # our best bet is to just retry.
                    continue

    def delete(self, entity: dict):
        entity_uuid: str = entity['uuid']
        with self._redisClient.pipeline() as pipe:
            while True:
                try:
                    # put a WATCH on the entity key (with a prefix because hash keys are not watchable)
                    pipe.watch('w:' + entity_uuid)
                    old_entity = pipe.hgetall('e:' + entity_uuid)
                    parent_uuid: str = pipe.get('p:' + entity_uuid)
                    print('Current entity:')
                    print(old_entity)
                    print('Parent:' + str(parent_uuid))
                    # now we can put the pipeline back into buffered mode with MULTI
                    pipe.multi()
                    pipe.set('w:' + entity_uuid, '')
                    for key, value in old_entity.items():
                        old_value = old_entity[key]
                        pipe.hdel('e:' + entity_uuid, key)
                        pipe.srem('i:' + key + ":" + old_value, entity_uuid)
                        print('Delete:' + str(key))

                    pipe.hdel('e:' + entity_uuid, '*')
                    print('Delete:' + entity_uuid)
                    # and finally, execute the pipeline (the set command)
                    pipe.delete('w:' + entity_uuid)
                    pipe.delete('p:' + entity_uuid)
                    pipe.srem('c:' + entity_uuid, '*')
                    # Unlink this entity from the parent
                    pipe.srem('c:' + parent_uuid, entity_uuid)
                    pipe.execute()
                    print('Update executed, version')
                    break
                except WatchError:
                    # another client must have changed the entity between
                    # the time we started WATCHing it and the pipeline's execution.
                    # our best bet is to just retry.
                    continue

    def get_entity_from_index(self, index_hit: str):
        print('Index lookup:' + index_hit)
        print('Index hit:' + str(self._redisClient.smembers(index_hit)))
        for entity_uuid in self._redisClient.smembers(index_hit):
            entity_key = 'e:' + entity_uuid
            entity: dict = self._redisClient.hgetall(entity_key)
            entity['uuid'] = entity_uuid
            yield entity

    def find(self, *args, **kwargs):
        filter_list = []
        for key in kwargs.keys():
            value = kwargs.get(key)
            if key == 'parent':
                filter_list.append('c:' + value)
            elif '*' in value or '?' in value or '[' in value:
                matching_keys = list(self._redisClient.scan_iter('i:' + key + ':' + value, count=1000))
                if len(matching_keys) > 0:
                    matching_key_set_name = 'u:' + str(uuid.uuid4())
                    print(matching_keys)
                    print(matching_key_set_name)
                    union_entity_cnt = self._redisClient.sunionstore(matching_key_set_name, matching_keys)
                    self._redisClient.expire(matching_key_set_name, 60)
                    if union_entity_cnt > 0:
                        filter_list.append(matching_key_set_name)
                    else:
                        # No matching keys = no result
                        self.logger.debug('No matching keys:' + key + '=' + value)
                        return filter_list
                else:
                    # No matching keys = no result
                    self.logger.debug('No entities in matching keys:' + key + '=' + value)
                    return filter_list
            else:
                filter_list.append('i:' + key + ':' + value)

        print('filter list:' + str(filter_list))
        for entity_uuid in self._redisClient.sinter(filter_list):
            print('Hit:' + entity_uuid)
            entity_key = 'e:' + entity_uuid
            entity: dict = self._redisClient.hgetall(entity_key)
            entity['uuid'] = entity_uuid
            yield entity

    def get_children(self, parent_uuid: str):
        for child_uuid in self._redisClient.smembers('c:' + parent_uuid):
            entity: dict = self._redisClient.hgetall('e:' + child_uuid)
            entity['uuid'] = child_uuid
            yield entity

    def get_parent(self, child_uuid: str):
        parent_uuid = self._redisClient.get('p:' + child_uuid)
        parent: dict = self._redisClient.hgetall('e:' + parent_uuid)
        parent['uuid'] = parent_uuid
        return parent
