#!/bin/sh
# Script to run tests using fakeredis (no Redis server required)

# Use the virtual environment Python if available
if [ -d ".venv/bin" ]; then
  echo "Using virtual environment in .venv/bin"
  source .venv/bin/activate
  PYTHON="python"
else
  echo "Using system Python"
  PYTHON="python"
fi

# Run pytest with fakeredis
echo "Running tests with fakeredis (no Redis server required)"
$PYTHON -m pytest tests/unit/ tests/integration/

# Exit with the pytest exit code
exit $? 