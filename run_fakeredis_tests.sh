#!/bin/sh
# Script to run tests using fakeredis (no Redis server required)

# Use the conda environment Python if available
if [ -d ".conda/bin" ]; then
  echo "Using conda environment in .conda/bin"
  PYTHON=".conda/bin/python"
else
  echo "Using system Python"
  PYTHON="python"
fi

# Run pytest with fakeredis
echo "Running tests with fakeredis (no Redis server required)"
$PYTHON -m pytest tests/unit/ tests/integration/

# Exit with the pytest exit code
exit $? 