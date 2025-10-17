# Repository Guidelines

## Project Structure & Module Organization
The `hotcore/` package houses the Redis-backed data model; key modules include `connection.py` for client management, `geospatial.py` and `h3_index.py` for spatial helpers, and `storage.py` for persistence primitives. Tests live under `tests/unit/` for fast fakeredis coverage and `tests/integration/` for broader flows, while sample scripts sit in the repository root (`hotcore_example_app.py`, `setup_integration.py`). Tooling and configuration are tracked at the top level via `pyproject.toml`, `pytest.ini`, and runner helpers such as `run_tests.sh`.

## Build, Test, and Development Commands
Create a local environment with `python -m venv .venv && source .venv/bin/activate`, then install dependencies using `pip install -e .[dev]` or `pip install -r requirements-dev.txt`. Run the default fakeredis suite with `./run_tests.sh`, target subsets via `./run_tests.sh --unit` or `./run_tests.sh tests/integration/test_relationships.py`, and switch to a real Redis instance using `./run_tests.sh --real-redis`. Package artifacts when needed with `python -m build` after confirming the version in `hotcore/_version.py`.

## Coding Style & Naming Conventions
All code targets Python 3.13 with 4-space indentation, 88-character lines, and trailing newline expectations enforced by Black and isort (`black hotcore tests` and `isort hotcore tests`). Prefer type hints throughout new APIs, keep module-level constants in `UPPER_SNAKE_CASE`, classes in `PascalCase`, and public callables in `snake_case`. Run `flake8` and `mypy` locally on touched paths before requesting review.

## Testing Guidelines
`pytest` is the canonical runner; filenames follow `test_*.py`, classes `Test*`, and functions `test_*` per `pytest.ini`. Use fakeredis-backed tests by default and mark real Redis dependencies with `@pytest.mark.redis_required`; when exercising them, ensure `redis-server` is running and export `USE_REAL_REDIS=true`. Aim to touch both unit and integration suites for model changes and collect coverage via `./run_tests.sh --cov` when adding substantial logic.

## Commit & Pull Request Guidelines
Write commit summaries in the imperative mood (e.g., `Add geospatial query helpers`) with optional bodies describing rationale or rollout steps. Every PR should outline the problem, link related issues, explain new Redis interactions or schema impacts, and list validation commands executed. Attach updated docs or screenshots when behavior changes, and request review once checks pass locally.
