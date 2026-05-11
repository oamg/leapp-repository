# Running Tests and Linters

All non-container commands (`make lint`, `make test_no_lint`, `make fast_lint`, `make dev_test_no_lint`) require a local virtualenv and `REPOSITORIES` envar (e.g. `REPOSITORIES=common,el9toel10`). Create the virtualenv with `make install-deps` (RHEL/CentOS) or `make install-deps-fedora` (Fedora) — the Makefile handles activation internally, don't source the venv manually. Set `PYTHON_VENV=pythonX.X` to choose the Python version (default: `python3.6`). Container commands are self-contained and recommended as the default.

## Container-based testing (CI-equivalent, no venv needed)

Three container options, each matching a target Python version:

| Container | Python | Used for |
|-----------|--------|----------|
| `el8`     | 3.6    | `common`, `el8toel9` |
| `el9`     | 3.9    | `common`, `el8toel9`, `el9toel10` |
| `f42`     | 3.13   | lint-only (latest tooling) |

Pick container(s) based on which repositories your change touches:
- `common` actors: test on `el8` **and** `el9` (both Python versions must pass).
- `el8toel9` only: `el8` is sufficient, `el9` is a bonus.
- `el9toel10` only: `el9`.

```bash
# Full test (lint + unit tests) in container — recommended
TEST_CONTAINER=el9 make test_container

# Tests only, skip lint — faster iteration
TEST_CONTAINER=el9 make test_container_no_lint

# All containers at once
make test_container_all
```

## Single-actor testing (fastest feedback, requires venv)

Use during development when iterating on one actor:

```bash
ACTOR=checkmemory make dev_test_no_lint
```

## Linting

```bash
# Lint in container (recommended, no venv needed)
make lint_container

# Full lint locally (requires venv): pylint + flake8 + isort
make lint

# Lint only local changes relative to main branch (requires venv)
make fast_lint

# Auto-fix isort violations locally (requires venv)
make lint_fix
```

## Choosing what to run

| Situation | Command |
|-----------|---------|
| Quick check during development | `ACTOR=<name> make dev_test_no_lint` |
| Before pushing | `TEST_CONTAINER=elX make test_container` |
| Full CI confidence | `make test_container_all` |
| Only lint issues | `make fast_lint` or `TEST_CONTAINER=elX make lint_container` |

## Interpreting failures

- **pylint / flake8**: fix the reported file and line.
- **isort**: run `make lint_fix` to auto-sort imports, then verify.
- **pytest**: read the traceback; check if the test uses `monkeypatch.setattr` correctly and if mocked models match current schema.