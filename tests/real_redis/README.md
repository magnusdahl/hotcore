# Redis Locking Tests

These tests verify that the optimistic locking mechanism in hotcore works correctly when multiple clients attempt to modify the same entity concurrently. They require a real Redis server to run.

## Prerequisites

- Docker (for running Redis locally) or a Redis server connection
- Python environment with pytest and all project dependencies installed

## Running the Tests

1. **Start a Redis server**

   Using Docker (recommended):

   ```bash
   docker run --name redis-test -p 6379:6379 -d redis
   ```

   Alternatively, you can use a Redis server you already have running locally or remotely.

2. **Run the tests**

   ```bash
   # Set environment variable to use real Redis
   export USE_REAL_REDIS=true
   
   # Run the locking tests
   python -m pytest tests/real_redis/test_locking.py -v
   
   # Run all real Redis tests 
   python -m pytest tests/real_redis/ -v
   ```

3. **Clean up**

   If you used Docker:

   ```bash
   docker stop redis-test
   docker rm redis-test
   ```

## Understanding the Tests

These tests verify that the optimistic locking mechanism using Redis WATCH correctly handles concurrent modification attempts:

1. `test_optimistic_locking_during_apply`: Tests that concurrent `apply` operations are handled correctly, with only one operation succeeding per entity attribute and others getting WatchError.

2. `test_optimistic_locking_during_delete`: Tests that concurrent `delete` operations are handled correctly, with only one operation succeeding.

3. `test_locking_with_custom_implementation`: Tests the locking mechanism directly using the `RedisConnectionManager` and `EntityStorage` classes for more fine-grained control.

## Notes

- The tests use threading to simulate concurrent operations.
- We purposely introduce a sleep to increase the likelihood of concurrent modification attempts.
- The test assertions verify that the final state of the entity is consistent with the expected outcome after concurrent operations. 