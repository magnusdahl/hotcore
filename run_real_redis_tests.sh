#!/bin/sh
# Script to run tests using a real Redis server

# Check if Redis is running
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Error: Redis server is not running or not accessible."
  echo "Please start Redis server before running these tests."
  exit 1
fi

# Use the conda environment Python if available
if [ -d ".conda/bin" ]; then
  echo "Using conda environment in .conda/bin"
  PYTHON=".conda/bin/python"
else
  echo "Using system Python"
  PYTHON="python"
fi

# Run pytest with real Redis
echo "Running tests with real Redis server"
USE_REAL_REDIS=true $PYTHON -m pytest

# Exit with the pytest exit code
exit $? 