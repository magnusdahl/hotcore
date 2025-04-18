# Packaging and Distribution Guide

This document provides instructions for building, testing, and publishing the hotcore package.

## Development Setup

We have two requirements files:
- `requirements.txt` - Contains only the minimal dependencies needed to use the package
- `requirements-dev.txt` - Contains all dependencies needed for development, testing, and building

For development, install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

Or install the package in development mode with all extras:

```bash
pip install -e ".[dev]"
```

## Building the Package

To build the package for distribution, follow these steps:

1. Ensure you have the necessary build tools installed:

```bash
pip install build twine
```

2. Build the package:

```bash
python -m build
```

This will create distribution packages in the `dist/` directory:
- `*.whl`: A wheel package (binary distribution)
- `*.tar.gz`: A source distribution

## Testing the Package

Before publishing, it's a good idea to verify the package by installing it locally:

```bash
# Install from the wheel file
pip install dist/hotcore-0.1.0-py3-none-any.whl

# Or install from the source distribution
pip install dist/hotcore-0.1.0.tar.gz
```

Then run some basic imports to verify it works:

```python
from hotcore import Model
model = Model(host='localhost')
print(model)
```

## Publishing to PyPI

1. First, test the upload to the PyPI test server:

```bash
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

2. Install from test PyPI to verify it works:

```bash
pip install --index-url https://test.pypi.org/simple/ hotcore
```

3. Once confirmed working, upload to the real PyPI:

```bash
python -m twine upload dist/*
```

## Versioning

When releasing new versions:

1. Update the version number in:
   - `hotcore/__init__.py` (`__version__` variable)
   - `setup.py` (`version` parameter)

2. Commit the changes:

```bash
git add hotcore/__init__.py setup.py
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

3. Build and publish the new version as described above.

## Development Installation

For development, install the package in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

This enables you to modify the code and have the changes immediately available without reinstalling. 