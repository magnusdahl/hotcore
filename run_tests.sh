#!/bin/bash
# Script to run tests for the hotcore project

set -e  # Exit on error

# Determine the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if venv is activated
if [[ -z "${VIRTUAL_ENV}" ]] || [[ "${VIRTUAL_ENV}" != *".venv"* ]]; then
    echo "⚠️  Virtual environment not activated. Activating .venv environment..."
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "❌ .venv directory not found. Please create a virtual environment first."
        echo "    You can use: python -m venv .venv"
        exit 1
    fi
fi

# Check for pytest
if ! python -c "import pytest" &>/dev/null; then
    echo "⚠️  pytest not found. Installing requirements..."
    pip install -r requirements-dev.txt
fi

# Check for fakeredis
if ! python -c "import fakeredis" &>/dev/null; then
    echo "⚠️  fakeredis not found. Installing..."
    pip install fakeredis
fi

# Default is to run all tests using fakeredis
USE_REAL_REDIS=false
TESTS_TO_RUN="tests/"
PYTEST_ARGS=""

# Process command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --real-redis)
            USE_REAL_REDIS=true
            shift
            ;;
        --unit)
            TESTS_TO_RUN="tests/unit/"
            shift
            ;;
        --integration)
            TESTS_TO_RUN="tests/integration/"
            shift
            ;;
        -v|--verbose)
            PYTEST_ARGS="$PYTEST_ARGS -v"
            shift
            ;;
        -x|--exitfirst)
            PYTEST_ARGS="$PYTEST_ARGS -x"
            shift
            ;;
        --cov)
            PYTEST_ARGS="$PYTEST_ARGS --cov=hotcore --cov-report=term-missing"
            shift
            ;;
        *)
            # Assume it's a specific test file or directory
            TESTS_TO_RUN="$1"
            shift
            ;;
    esac
done

# Export environment variables
if [ "$USE_REAL_REDIS" = true ]; then
    export USE_REAL_REDIS=true
    echo "🔄 Running tests with real Redis..."
else
    export USE_REAL_REDIS=false
    echo "🔄 Running tests with fakeredis..."
fi

# Run the tests
echo "🔄 Running tests: $TESTS_TO_RUN"
python -m pytest $TESTS_TO_RUN $PYTEST_ARGS

# Check if tests passed
if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed."
    exit 1
fi 