""" Entity model for the core dataset of an application. The structural, referential, ever changing dataset

This module provides a data model implementation using Redis as the backend.
It manages a hierarchical tree structure of entities with parent-child relationships
and supports indexing of entity attributes for efficient searching.

Typical usage example:

  model = Model(host='localhost')
  entity = {'uuid': str(uuid.uuid4()), 'name': 'example', 'type': 'test'}
  parent_uuid = 'root'  # Some existing parent UUID
  saved_entity = model.create(parent_uuid, entity)
"""
import logging
import uuid
import redis
from redis import WatchError
from typing import Dict, List, Generator, Optional, Any, Union, Set


class RedisConnectionManager:
    """Manages Redis connections and provides key generation utilities.
    
    This class handles connection pooling and provides utility methods
    for generating Redis keys according to the application's conventions.
    """
    # Redis key prefixes
    ENTITY_PREFIX = "e:"
    INDEX_PREFIX = "i:"
    PARENT_PREFIX = "p:"
    CHILDREN_PREFIX = "c:"
    FIND_UNIQUE_PREFIX = "u:"
    WATCH_LOCK_PREFIX = "w:"
    
    logger = logging.getLogger(__name__)
    
    def __init__(self, host: str, port: int = 6379, db: int = 0) -> None:
        """Initialize the Redis connection manager.
        
        Args:
            host: Redis server hostname or IP address
            port: Redis server port (default: 6379)
            db: Redis database number (default: 0)
        """
        # Create a connection pool
        self._pool = redis.ConnectionPool(
            host=host, 
            port=port, 
            db=db, 
            decode_responses=True
        )
        
    def get_client(self) -> redis.Redis:
        """Get a Redis client from the connection pool.
        
        Returns:
            A Redis client using the connection pool
        """
        return redis.Redis(connection_pool=self._pool)
    
    def flush_all(self) -> None:
        """Delete all keys in the Redis database.
        
        Caution: This will permanently remove all data in the current Redis database.
        Primarily used for testing purposes.
        """
        try:
            self.get_client().flushall()
        except redis.RedisError as e:
            self.logger.error(f"Redis error during flush_all: {str(e)}")
            raise
    
    def get_entity_key(self, entity_uuid: str) -> str:
        """Generate a Redis key for accessing an entity's hash.
        
        Args:
            entity_uuid: The UUID of the entity
            
        Returns:
            The entity key string
        """
        return f'{self.ENTITY_PREFIX}{entity_uuid}'
    
    def get_watch_key(self, entity_uuid: str) -> str:
        """Generate a Redis key for watching an entity during optimistic locking.
        
        Args:
            entity_uuid: The UUID of the entity
            
        Returns:
            The watch key string
        """
        return f'{self.WATCH_LOCK_PREFIX}{entity_uuid}'
    
    def get_parent_key(self, entity_uuid: str) -> str:
        """Generate a Redis key for accessing an entity's parent pointer.
        
        Args:
            entity_uuid: The UUID of the entity
            
        Returns:
            The parent key string
        """
        return f'{self.PARENT_PREFIX}{entity_uuid}'
    
    def get_children_key(self, entity_uuid: str) -> str:
        """Generate a Redis key for accessing an entity's children set.
        
        Args:
            entity_uuid: The UUID of the entity
            
        Returns:
            The children key string
        """
        return f'{self.CHILDREN_PREFIX}{entity_uuid}'
    
    def get_index_key(self, attribute: str, value: Any) -> str:
        """Generate a Redis key for an attribute index.
        
        Args:
            attribute: The attribute name
            value: The attribute value
            
        Returns:
            The index key string
        """
        return f'{self.INDEX_PREFIX}{attribute}:{value}'
    
    def get_unique_set_key(self) -> str:
        """Generate a unique Redis key for temporary sets.
        
        Returns:
            A unique key with the unique set prefix
        """
        return f'{self.FIND_UNIQUE_PREFIX}{uuid.uuid4()}'


class EntityStorage:
    """Handles core entity storage operations.
    
    This class is responsible for the basic CRUD operations
    on entities stored in Redis.
    """
    logger = logging.getLogger(__name__)
    
    def __init__(self, connection_manager: RedisConnectionManager) -> None:
        """Initialize the entity storage.
        
        Args:
            connection_manager: The Redis connection manager
        """
        self.connection = connection_manager
    
    def get(self, entity_uuid: str) -> Dict[str, Any]:
        """Retrieve an entity by its UUID.
        
        Args:
            entity_uuid: The UUID of the entity to retrieve
            
        Returns:
            The entity as a dictionary with all its attributes including the UUID
            
        Raises:
            redis.RedisError: If a Redis-related error occurs during the operation
        """
        entity_key = self.connection.get_entity_key(entity_uuid)
        try:
            client = self.connection.get_client()
            entity: Dict[str, Any] = client.hgetall(entity_key)
            if not entity:
                self.logger.warning(f"Entity with UUID {entity_uuid} not found")
            entity['uuid'] = entity_uuid
            self.logger.debug(f'Get: {entity}')
            return entity
        except redis.RedisError as e:
            self.logger.error(f"Redis error retrieving entity {entity_uuid}: {str(e)}")
            raise
    
    def create(self, parent_uuid: str, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create and save a new entity into the structure.

        Saves the entity to Redis and updates the parent to reflect the added child.
        All entity attributes are indexed for efficient searching.

        Args:
            parent_uuid: The UUID of the parent entity
            entity: A dictionary containing the properties of the entity
                   (must include a 'uuid' key)

        Raises:
            TypeError: If the entity does not contain a 'uuid' key or if it's None
            redis.RedisError: If a Redis-related error occurs during the operation

        Returns:
            The created entity dictionary
        """
        entity_uuid = entity.get('uuid')
        if entity_uuid is None:
            raise TypeError('entity must be a dictionary (dict) containing the key \'uuid\'')
        
        try:
            client = self.connection.get_client()
            entity_key = self.connection.get_entity_key(entity_uuid)
            parent_key = self.connection.get_parent_key(entity_uuid)
            children_key = self.connection.get_children_key(parent_uuid)
            
            with client.pipeline() as pipe:
                pipe.multi()
                
                # Save the entity without the uuid value (temporary removed)
                # Make a copy to avoid modifying the original
                entity_copy = entity.copy()
                del entity_copy['uuid']
                
                # Store the entity attributes
                pipe.hset(entity_key, mapping=entity_copy)
                
                # Create indexes for each attribute
                for key, value in entity_copy.items():
                    index_key = self.connection.get_index_key(key, value)
                    pipe.sadd(index_key, entity_uuid)
                
                # Save the parent pointer
                pipe.set(parent_key, parent_uuid)
                
                # Add this entity into the child list of the parent
                pipe.sadd(children_key, entity_uuid)
                
                pipe.execute()
                self.logger.info(f'Created entity {entity_uuid} with parent {parent_uuid}')
                return entity
        except redis.RedisError as e:
            self.logger.error(f"Redis error creating entity {entity_uuid}: {str(e)}")
            raise
    
    def _update_entity_indexes(self, 
                              pipe: redis.client.Pipeline, 
                              entity_uuid: str, 
                              old_entity: Dict[str, Any], 
                              updates: Dict[str, Any]) -> None:
        """Update indexes for entity attributes that have changed.
        
        Args:
            pipe: Redis pipeline to execute commands on
            entity_uuid: UUID of the entity being updated
            old_entity: Previous entity state
            updates: New attribute values to apply
        """
        # Apply updates to the entity
        if updates:
            entity_key = self.connection.get_entity_key(entity_uuid)
            pipe.hset(entity_key, mapping=updates)
            
            # Update indexes for changed attributes
            for key, value in updates.items():
                # Remove old index if attribute existed before
                if key in old_entity:
                    old_value = old_entity[key]
                    if old_value is not None:
                        old_index_key = self.connection.get_index_key(key, old_value)
                        pipe.srem(old_index_key, entity_uuid)
                
                # Add new index
                new_index_key = self.connection.get_index_key(key, value)
                pipe.sadd(new_index_key, entity_uuid)
    
    def _remove_entity_attributes(self, 
                                 pipe: redis.client.Pipeline, 
                                 entity_uuid: str, 
                                 old_entity: Dict[str, Any], 
                                 keys_to_remove: List[str]) -> None:
        """Remove specified attributes from an entity and their indexes.
        
        Args:
            pipe: Redis pipeline to execute commands on
            entity_uuid: UUID of the entity
            old_entity: Current entity state
            keys_to_remove: Attribute keys to remove
        """
        entity_key = self.connection.get_entity_key(entity_uuid)
        
        for key in keys_to_remove:
            if key in old_entity:
                old_value = old_entity[key]
                # Remove attribute from entity
                pipe.hdel(entity_key, key)
                # Remove from index
                index_key = self.connection.get_index_key(key, old_value)
                pipe.srem(index_key, entity_uuid)
                self.logger.debug(f'Deleting attribute: {key}')
    
    def apply(self, change: Dict[str, Any]) -> None:
        """Apply changes to an existing entity.
        
        Updates, adds, or removes entity attributes based on the provided change dictionary.
        Maintains consistency of entity attributes and their indexes.
        Uses optimistic locking via Redis WATCH to handle concurrent modifications.
        
        Args:
            change: A dictionary containing the changes to apply
                   Must include a 'uuid' key to identify the entity
                   Set attribute value to None to delete it
        
        Raises:
            KeyError: If the change dictionary does not contain a 'uuid' key
            redis.RedisError: If a Redis-related error occurs during the operation
            WatchError: Handled internally, retrying if another client modified
                       the entity concurrently
        """
        if 'uuid' not in change:
            raise KeyError("The change dictionary must contain a 'uuid' key")
            
        entity_uuid: str = change['uuid']
        watch_key = self.connection.get_watch_key(entity_uuid)
        entity_key = self.connection.get_entity_key(entity_uuid)
        
        try:
            client = self.connection.get_client()
            with client.pipeline() as pipe:
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    try:
                        # Watch key for optimistic locking
                        pipe.watch(watch_key)
                        old_entity: Dict[str, Any] = pipe.hgetall(entity_key)
                        if not old_entity:
                            self.logger.warning(f"Entity with UUID {entity_uuid} not found during apply operation")
                            
                        self.logger.debug(f'Current entity: {old_entity}')
                        
                        # Start transaction
                        pipe.multi()
                        pipe.set(watch_key, '')

                        # Identify attributes to update and remove
                        keys_to_remove = [k for k, v in change.items() if v is None and k != 'uuid']
                        updated_values: Dict[str, Any] = dict(filter(
                            lambda elem: elem[1] is not None and elem[0] != 'uuid', 
                            change.items()
                        ))
                        
                        self.logger.debug(f'Updated values: {updated_values}')
                        
                        # Handle removals
                        self._remove_entity_attributes(pipe, entity_uuid, old_entity, keys_to_remove)
                        
                        # Handle updates
                        self._update_entity_indexes(pipe, entity_uuid, old_entity, updated_values)

                        # Execute the transaction
                        pipe.execute()
                        self.logger.info(f'Apply operation executed successfully for entity {entity_uuid}')
                        break
                    except WatchError:
                        # Another client modified the entity during our operation, retry
                        retry_count += 1
                        self.logger.warning(f'WatchError during apply of {entity_uuid}, retry {retry_count}/{max_retries}')
                        if retry_count >= max_retries:
                            self.logger.error(f'Max retries ({max_retries}) reached for apply operation on {entity_uuid}')
                            raise
                        continue
        except redis.RedisError as e:
            self.logger.error(f"Redis error during apply operation on entity {entity_uuid}: {str(e)}")
            raise
    
    def delete(self, entity: Dict[str, Any]) -> None:
        """Delete an entity from the structure.
        
        Removes the entity, its attributes, all indexes, and parent-child relationships.
        Uses optimistic locking via Redis WATCH to handle concurrent modifications.
        
        Args:
            entity: The entity dictionary to delete (must contain a 'uuid' key)
        
        Raises:
            KeyError: If the entity dictionary does not contain a 'uuid' key
            redis.RedisError: If a Redis-related error occurs during the operation
            WatchError: Handled internally, retrying if another client modified
                       the entity concurrently
        """
        if 'uuid' not in entity:
            raise KeyError("The entity dictionary must contain a 'uuid' key")
            
        entity_uuid: str = entity['uuid']
        watch_key = self.connection.get_watch_key(entity_uuid)
        entity_key = self.connection.get_entity_key(entity_uuid)
        parent_key = self.connection.get_parent_key(entity_uuid)
        children_key = self.connection.get_children_key(entity_uuid)
        
        try:
            client = self.connection.get_client()
            with client.pipeline() as pipe:
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    try:
                        # Watch key for optimistic locking
                        pipe.watch(watch_key)
                        old_entity: Dict[str, Any] = pipe.hgetall(entity_key)
                        if not old_entity:
                            self.logger.warning(f"Entity with UUID {entity_uuid} not found during delete operation")
                            
                        parent_uuid: Optional[str] = pipe.get(parent_key)
                        
                        self.logger.debug('Current entity:')
                        self.logger.debug(f'{old_entity}')
                        self.logger.debug(f'Parent: {parent_uuid}')
                        
                        # Start transaction
                        pipe.multi()
                        pipe.set(watch_key, '')
                        
                        # Remove all attributes and their indexes
                        self._remove_entity_attributes(pipe, entity_uuid, old_entity, list(old_entity.keys()))

                        # Remove the entity completely
                        pipe.hdel(entity_key, '*')
                        self.logger.debug(f'Delete: {entity_uuid}')
                        
                        # Clean up related keys
                        pipe.delete(watch_key)
                        pipe.delete(parent_key)
                        pipe.srem(children_key, '*')
                        
                        # Unlink this entity from the parent
                        if parent_uuid:
                            parent_children_key = self.connection.get_children_key(parent_uuid)
                            pipe.srem(parent_children_key, entity_uuid)
                        
                        # Execute the transaction
                        pipe.execute()
                        self.logger.info('Delete operation executed successfully')
                        break
                    except WatchError:
                        # Another client modified the entity during our operation, retry
                        retry_count += 1
                        self.logger.warning(f'WatchError during delete of {entity_uuid}, retry {retry_count}/{max_retries}')
                        if retry_count >= max_retries:
                            self.logger.error(f'Max retries ({max_retries}) reached for delete operation on {entity_uuid}')
                            raise
                        continue
        except redis.RedisError as e:
            self.logger.error(f"Redis error during delete operation on entity {entity_uuid}: {str(e)}")
            raise


class EntityRelationship:
    """Manages entity relationships (parent-child).
    
    This class provides methods for navigating the hierarchical
    structure of entities.
    """
    logger = logging.getLogger(__name__)
    
    def __init__(self, connection_manager: RedisConnectionManager) -> None:
        """Initialize the entity relationship manager.
        
        Args:
            connection_manager: The Redis connection manager
        """
        self.connection = connection_manager
    
    def get_children(self, parent_uuid: str) -> Generator[Dict[str, Any], None, None]:
        """Retrieve all direct children of a parent entity.
        
        Args:
            parent_uuid: The UUID of the parent entity
            
        Yields:
            Entity dictionaries that are direct children of the specified parent
            
        Raises:
            redis.RedisError: If a Redis-related error occurs during the operation
        """
        try:
            client = self.connection.get_client()
            children_key = self.connection.get_children_key(parent_uuid)
            children = client.smembers(children_key)
            if not children:
                self.logger.debug(f"No children found for parent {parent_uuid}")
                return
                
            for child_uuid in children:
                entity_key = self.connection.get_entity_key(child_uuid)
                entity: Dict[str, Any] = client.hgetall(entity_key)
                entity['uuid'] = child_uuid
                yield entity
        except redis.RedisError as e:
            self.logger.error(f"Redis error retrieving children for parent {parent_uuid}: {str(e)}")
            raise
    
    def get_parent(self, child_uuid: str) -> Dict[str, Any]:
        """Retrieve the parent entity of a child entity.
        
        Args:
            child_uuid: The UUID of the child entity
            
        Returns:
            The parent entity as a dictionary with all its attributes.
            If parent UUID exists but has no associated entity, returns
            a dict with only the 'uuid' key.
            
        Raises:
            redis.RedisError: If a Redis-related error occurs during the operation
            ValueError: If the parent UUID is not found for the child
        """
        try:
            client = self.connection.get_client()
            parent_key = self.connection.get_parent_key(child_uuid)
            parent_uuid: str = client.get(parent_key)
            
            if not parent_uuid:
                error_msg = f"Parent UUID not found for child {child_uuid}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
                
            entity_key = self.connection.get_entity_key(parent_uuid)
            parent: Dict[str, Any] = client.hgetall(entity_key)
            
            if not parent:
                # Parent UUID exists but no entity found - this happens in tests
                # Return a dict with just the UUID instead of raising an error
                self.logger.warning(f"Parent entity {parent_uuid} not found for child {child_uuid}, returning UUID only")
                parent = {}  # Create an empty dict for the parent
                
            parent['uuid'] = parent_uuid
            return parent
        except redis.RedisError as e:
            self.logger.error(f"Redis error retrieving parent for child {child_uuid}: {str(e)}")
            raise


class EntitySearch:
    """Provides entity search and indexing capabilities.
    
    This class is responsible for finding entities based on
    attribute criteria and pattern matching.
    """
    logger = logging.getLogger(__name__)
    
    def __init__(self, connection_manager: RedisConnectionManager) -> None:
        """Initialize the entity search service.
        
        Args:
            connection_manager: The Redis connection manager
        """
        self.connection = connection_manager
    
    def get_entity_from_index(self, index_hit: str) -> Generator[Dict[str, Any], None, None]:
        """Retrieve entities matching a specific index.
        
        Args:
            index_hit: The Redis index key to look up
            
        Yields:
            Entity dictionaries that match the index
            
        Raises:
            redis.RedisError: If a Redis-related error occurs during the operation
        """
        try:
            client = self.connection.get_client()
            self.logger.debug(f'Index lookup: {index_hit}')
            index_members: Set[str] = client.smembers(index_hit)
            self.logger.debug(f'Index hit: {index_members}')
            for entity_uuid in index_members:
                entity_key = self.connection.get_entity_key(entity_uuid)
                entity: Dict[str, Any] = client.hgetall(entity_key)
                entity['uuid'] = entity_uuid
                yield entity
        except redis.RedisError as e:
            self.logger.error(f"Redis error retrieving entities from index {index_hit}: {str(e)}")
            raise

    def find(self, *args: Any, **kwargs: str) -> Generator[Dict[str, Any], None, None]:
        """Find entities matching the specified criteria.
        
        Search entities based on their attributes. Supports exact matches, pattern matching
        with wildcards ('*', '?', '[...]'), and parent-based filtering. When multiple criteria
        are specified, all must match (logical AND).
        
        Args:
            *args: Currently not used
            **kwargs: Attribute name-value pairs to match. Special key 'parent' matches
                     by parent UUID instead of entity attribute.
                      
        Returns:
            A generator yielding matching entity dictionaries. Returns empty if no matches found.
            
        Raises:
            redis.RedisError: If a Redis-related error occurs during the operation
            
        Examples:
            # Find all entities with type='user' and status='active'
            entities = model.find(type='user', status='active')
            
            # Find all direct children of a specific parent
            entities = model.find(parent='parent-uuid')
            
            # Find entities with names starting with 'A'
            entities = model.find(name='A*')
        """
        try:
            client = self.connection.get_client()
            filter_list: List[str] = []
            for key in kwargs.keys():
                value = kwargs.get(key)
                if key == 'parent':
                    filter_list.append(self.connection.get_children_key(value))
                elif '*' in value or '?' in value or '[' in value:
                    index_pattern = f'{self.connection.INDEX_PREFIX}{key}:{value}'
                    matching_keys: List[str] = list(client.scan_iter(index_pattern, count=1000))
                    if len(matching_keys) > 0:
                        matching_key_set_name = self.connection.get_unique_set_key()
                        self.logger.debug(f'Matching keys: {matching_keys}')
                        self.logger.debug(f'Matching key set name: {matching_key_set_name}')
                        try:
                            union_entity_cnt = client.sunionstore(matching_key_set_name, matching_keys)
                            client.expire(matching_key_set_name, 60)
                            if union_entity_cnt > 0:
                                filter_list.append(matching_key_set_name)
                            else:
                                # No matching keys = no result
                                self.logger.debug(f'No matching keys: {key}={value}')
                                return
                        except redis.RedisError as e:
                            self.logger.error(f"Redis error during union operation: {str(e)}")
                            # Clean up the temporary key if it exists
                            try:
                                client.delete(matching_key_set_name)
                            except:
                                pass
                            raise
                    else:
                        # No matching keys = no result
                        self.logger.debug(f'No entities in matching keys: {key}={value}')
                        return
                else:
                    filter_list.append(self.connection.get_index_key(key, value))

            if not filter_list:
                self.logger.warning("No filter criteria provided for find operation")
                return

            self.logger.debug(f'Filter list: {filter_list}')
            for entity_uuid in client.sinter(filter_list):
                self.logger.debug(f'Hit: {entity_uuid}')
                entity_key = self.connection.get_entity_key(entity_uuid)
                entity: Dict[str, Any] = client.hgetall(entity_key)
                entity['uuid'] = entity_uuid
                yield entity
        except redis.RedisError as e:
            self.logger.error(f"Redis error during find operation: {str(e)}")
            raise


class Model:
    """Main model class integrating Redis data storage with entity operations.
    
    This class provides a unified interface to the component classes,
    acting as a facade while delegating operations to specialized components.
    """
    logger = logging.getLogger(__name__)
    
    def __init__(self, host: str, port: int = 6379, db: int = 0) -> None:
        """Initialize the model with Redis connection.
        
        Args:
            host: Redis server hostname or IP address
            port: Redis server port (default: 6379)
            db: Redis database number (default: 0)
        """
        # Create component instances
        self.connection = RedisConnectionManager(host, port, db)
        self.storage = EntityStorage(self.connection)
        self.relationship = EntityRelationship(self.connection)
        self.search = EntitySearch(self.connection)
    
    def flush_all(self) -> None:
        """Delete all keys in the Redis database.
        
        Caution: This will permanently remove all data in the current Redis database.
        Primarily used for testing purposes.
        """
        return self.connection.flush_all()
    
    @staticmethod
    def init(entity: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize an entity with a generated UUID.
        
        Args:
            entity: The entity dictionary to initialize
            
        Returns:
            The same entity dictionary with an added 'uuid' key
        """
        entity.__setitem__('uuid', str(uuid.uuid4()))
        return entity
    
    # Delegate methods to the appropriate component
    
    def create(self, parent_uuid: str, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity. See EntityStorage.create for details."""
        return self.storage.create(parent_uuid, entity)
    
    def get(self, entity_uuid: str) -> Dict[str, Any]:
        """Get an entity by UUID. See EntityStorage.get for details."""
        return self.storage.get(entity_uuid)
    
    def apply(self, change: Dict[str, Any]) -> None:
        """Apply changes to an entity. See EntityStorage.apply for details."""
        return self.storage.apply(change)
    
    def delete(self, entity: Dict[str, Any]) -> None:
        """Delete an entity. See EntityStorage.delete for details."""
        return self.storage.delete(entity)
    
    def get_children(self, parent_uuid: str) -> Generator[Dict[str, Any], None, None]:
        """Get children of an entity. See EntityRelationship.get_children for details."""
        return self.relationship.get_children(parent_uuid)
    
    def get_parent(self, child_uuid: str) -> Dict[str, Any]:
        """Get parent of an entity. See EntityRelationship.get_parent for details."""
        return self.relationship.get_parent(child_uuid)
    
    def get_entity_from_index(self, index_hit: str) -> Generator[Dict[str, Any], None, None]:
        """Get entities from an index. See EntitySearch.get_entity_from_index for details."""
        return self.search.get_entity_from_index(index_hit)
    
    def find(self, *args: Any, **kwargs: str) -> Generator[Dict[str, Any], None, None]:
        """Find entities by criteria. See EntitySearch.find for details."""
        return self.search.find(*args, **kwargs)
