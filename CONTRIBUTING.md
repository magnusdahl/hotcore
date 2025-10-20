# Contributing to hotcore

We love community contributions! This guide outlines how to set up your development environment, follow the project conventions, and submit improvements confidently.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.

## Development Environment

1. **Prerequisites**
   - Python 3.10+
   - Redis (local or remote) if you plan to run integration tests against a live server
   - `make`, `git`, and a C compiler if you plan to install optional dependencies from source

2. **Clone the repository**

   ```bash
   git clone https://github.com/Consistis-R-D/hotcore.git
   cd hotcore
   ```

3. **Create a virtual environment**

   ```bash
   python3.10 -m venv .venv
   source .venv/bin/activate
   ```

4. **Install dependencies**

   ```bash
   # Core + developer tooling
   pip install -e ".[dev]"

   # Optional: enable H3 features
   pip install -e ".[h3]"
   ```

## Project Layout

```
hotcore/
├── connection.py       # Redis connection + key helpers
├── storage.py          # CRUD and attribute indexing
├── relationships.py    # Parent/child helpers
├── search.py           # Attribute-based search utilities
├── geospatial.py       # Redis GEO management
├── h3_index.py         # Optional H3 indexing support
├── model.py            # Facade wiring the components together
└── hotcore.py          # Backwards-compatible import surface
```

Unit and integration tests live under `tests/`. See `tests/README.md` for details.

## Coding Standards

- **Formatting**: `black` (line length 88) and `isort` (profile `black`).
- **Linting**: `flake8`.
- **Type checking**: `mypy`. Optional dependencies use feature-gated type hints; run `pip install -e ".[h3]"` before `mypy` if you are touching H3 functionality.
- **Docstrings**: follow PEP 257. Public APIs should have clear docstrings; internal helpers may use concise comments where helpful.
- **Logging**: use the module-level `logging` instance instead of `print`.

We recommend installing [pre-commit](https://pre-commit.com/) to automate formatting:

```bash
pip install pre-commit
pre-commit install
```

_(A `.pre-commit-config.yaml` will be added soon—feel free to help implement it!)_

## Testing

Run tests in an activated virtual environment:

```bash
pytest                    # Fakeredis-backed unit + integration tests
pytest tests/unit/        # Only unit tests
pytest tests/integration/ # Only integration tests
```

To exercise features that require a real Redis server:

```bash
export USE_REAL_REDIS=true
export REDIS_HOST=localhost  # override as needed
pytest                       # includes tests/real_redis when marker enabled
```

Automated test utilities:

- `./run_tests.sh` – convenience wrapper with coverage and Redis options.
- `./run_fakeredis_tests.sh` / `./run_real_redis_tests.sh` – pared-down helpers.

### Adding Tests

- Prefer unit tests with fakeredis where possible.
- Mark tests that need Redis with `@pytest.mark.redis_required` and place them in `tests/real_redis/`.
- If you add optional dependency support (e.g., H3), add tests that are skipped when the dependency is missing and run them locally with the extra installed.

## Pull Request Checklist

Before submitting a PR:

1. Format the code: `black .` and `isort .`.
2. Run `flake8` and `mypy`.
3. Run `pytest` (and real-Redis tests where relevant).
4. Update documentation, changelog, or tests if behaviour changes.
5. Ensure commits are tidy and references (issues, discussions) are linked in your PR description.

## Reporting Bugs & Requesting Features

- **Bugs**: File an issue using the "Bug report" template. Include reproduction steps, observed/expected behaviour, and environment details.
- **Features**: Open a feature request to describe the use case, proposed API, and any alternatives considered.

## Release Process (Maintainers)

1. Update `hotcore/_version.py`.
2. Run the full test suite (fakeredis + real Redis if applicable).
3. `python -m build` and validate distributions in a clean environment.
4. `twine upload` to Test PyPI, smoke test, then upload to PyPI.
5. Create a Git tag `vX.Y.Z` and draft release notes.

Thank you for helping improve hotcore! If anything is unclear or you need guidance, please open a discussion or issue. We're happy to collaborate. 🙂
