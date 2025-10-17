# Testing Hotcore

This directory contains unit and integration tests for the Hotcore package.

## Test Structure

The tests are organized into the following directories:

- `unit/`: Unit tests that test individual components in isolation
- `integration/`: Integration tests that test the system as a whole
- `real_redis/`: Tests that require a real Redis server to run

## Running Tests

### Using the run_tests.sh Script

The easiest way to run tests is using the provided script:

```bash
# Run all tests with fakeredis (real_redis tests will be skipped)
./run_tests.sh

# Run only unit tests
./run_tests.sh --unit

# Run only integration tests
./run_tests.sh --integration

# Run with verbose output
./run_tests.sh -v

# Run with coverage report
./run_tests.sh --cov

# Run with a real Redis server
./run_tests.sh --real-redis
```

The script will automatically check for and activate the virtual environment in `.venv` if it exists.

### Using pytest Directly with Virtual Environment

If you prefer to run pytest commands directly:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run all tests (real_redis tests will be skipped)
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run a specific test file
pytest tests/unit/test_model_unit.py

# Run a specific test
pytest tests/unit/test_model_unit.py::TestModelUnit::test_create_and_get
```

### Using fakeredis (Default)

By default, tests run using fakeredis which doesn't require a real Redis server:

```bash
# Run all tests (real_redis tests will be skipped)
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run a specific test file
pytest tests/unit/test_model_unit.py

# Run a specific test
pytest tests/unit/test_model_unit.py::TestModelUnit::test_create_and_get
```

### Using a Real Redis Server

To run tests against a real Redis server:

```bash
# Set the environment variable to use a real Redis server
export USE_REAL_REDIS=true

# Optionally, specify the Redis host
export REDIS_HOST=localhost

# Run all tests including real_redis tests
pytest

# Run only tests that require a real Redis server
pytest tests/real_redis/
```

**Warning:** Running tests with a real Redis server will flush all data in the specified Redis database. Make sure you're not pointing to a production database!

## Test Categories

### 1. Unit Tests (`tests/unit/`)

These tests focus on individual components and use fakeredis to avoid requiring a real Redis server. They test basic functionality in isolation.

**Key Test Files:**
- `test_geospatial.py` - Comprehensive tests for geospatial functionality (28 tests)
- `test_model_components.py` - Tests for individual component classes
- `test_model_basic.py` - Basic model operations
- `test_model_error_handling.py` - Error handling and edge cases
- `test_connection_manager.py` - Redis connection management

### 2. Integration Tests (`tests/integration/`)

These tests exercise more complex functionality and interactions between components but still use fakeredis, so they don't require a real Redis server.

### 3. Real Redis Tests (`tests/real_redis/`)

These tests are marked with the `@pytest.mark.redis_required` decorator and require a real Redis server to run. They test functionality that cannot be adequately tested with fakeredis, such as complex searches and performance characteristics.

## Writing New Tests

When writing tests, follow these guidelines:

1. **Use fixtures**: The `conftest.py` file provides fixtures for Redis connections and model instances. Use these fixtures in your tests.

2. **Clean up**: Tests should clean up after themselves. The fixtures automatically flush Redis before and after each test.

3. **Isolation**: Tests should be independent of each other. Don't rely on state from previous tests.

4. **Redis Requirements**: 
   - If your test can work with fakeredis, put it in `unit/` or `integration/`
   - If your test requires a real Redis server, put it in `real_redis/` and mark it with `@pytest.mark.redis_required`

5. **Conditional Tests**: Use `pytest.skip()` for tests that have additional requirements beyond Redis.

## Geospatial Testing

The geospatial functionality is thoroughly tested with **28 comprehensive test cases** in `tests/unit/test_geospatial.py`:

### Test Coverage

- **`TestGeospatialManager`**: Tests the core geospatial manager in isolation
  - Coordinate validation and detection
  - Adding/removing entities from geospatial index
  - Bounding box search functionality
  - Error handling and edge cases

- **`TestModelGeospatialIntegration`**: Tests integration with the main Model class
  - Automatic indexing during entity creation
  - Automatic updates when coordinates change
  - Proper handling of entities without coordinates
  - Search functionality integration

- **`TestGeospatialEdgeCases`**: Tests boundary conditions and edge cases
  - Coordinate precision handling
  - Boundary value validation
  - Small and large bounding box scenarios

### Running Geospatial Tests

```bash
# Run just the geospatial tests
pytest tests/unit/test_geospatial.py -v

# Run with coverage
pytest tests/unit/test_geospatial.py --cov=hotcore.hotcore --cov-report=term-missing
```

### Test Quality Features

- **Proper mocking**: Uses `unittest.mock` to isolate tests from Redis dependencies
- **Realistic test data**: Coordinates that actually fall within test bounding boxes
- **Comprehensive assertions**: Tests both positive and negative cases
- **Integration testing**: Verifies that geospatial features work with existing codebase
- **Error scenario coverage**: Tests various failure modes and edge cases 
