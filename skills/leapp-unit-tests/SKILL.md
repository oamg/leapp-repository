# Writing Unit Tests


## File placement

### Tests for actors

Tests live in the tests directory under an actor:

```
repos/system_upgrade/<leapp_repo_dir>/actors/<actor_name>/
├── actor.py
├── libraries/<actor_name>.py
└── tests/test_<actor_name>.py      # <-- tests go here
```

### Tests for shared libraries

Tests for shared libraries are in the `tests` sub-directory next to the shared library, like:

```
repos/system_upgrade/<leapp_repo_dir>/
├── <libA>.py
├── tests/test_<libA>.py      # <-- tests for libA go here
├── <pathB>/<libB>.py
└── <pathB>/tests/test_<libB>.py      # <-- tests for libB go here
```

## Key testing utilities

As mocked objects, use functions and classes present in `leapp.libraries.common.testutils` - especially:

| Utility                   | Purpose                                                    |
| ------------------------- | ---------------------------------------------------------- |
| `CurrentActorMocked(...)` | Mock `api.current_actor` with configuration, version, etc. |
| `produce_mocked()`        | Capture `api.produce(...)` calls for assertions            |
| `create_report_mocked()`  | Capture `reporting.create_report(...)` calls               |
| `logger_mocked()`         | Capture log output                                         |


## Standard test pattern

Test the **library**, not the actor class directly:

```python
from leapp.libraries.actor import <actor_lib>
from leapp.libraries.common.testutils import CurrentActorMocked, produce_mocked
from leapp.libraries.stdlib import api
from leapp.models import <ConsumedModel>, <ProducedModel>


def test_<scenario>(monkeypatch):
    # 1. Mock current_actor context
    monkeypatch.setattr(api, 'current_actor', CurrentActorMocked())

    # 2. Mock consumed messages
    monkeypatch.setattr(api, 'consume', lambda x: iter([<ConsumedModel>(...)]))

    # 3. Mock produce
    monkeypatch.setattr(api, 'produce', produce_mocked())

    # 4. Call library function
    <actor_lib>.process()

    # 5. Assert on produced messages
    assert api.produce.called
    assert isinstance(api.produce.model_instances[0], <ProducedModel>)
```

## Rules


- Test the library, not `actor.py` — the `process()` method should be a thin wrapper.
- Pass consumed messages via `CurrentActorMocked(msgs=[...])`.
- Mock file I/O instead of creating temp files when possible. Use the `leapp_tmpdir` fixture when tempfiles are needed.
- Use `monkeypatch.setattr` over `unittest.mock.patch` — monkeypatch is the project convention.
- Cover at least: happy path, edge/error cases, and inhibitor conditions if applicable.
- If you intentionally skip a test scenario, add a comment explaining why.
- Use consistent string quoting within a file.
- Use pytest.mark.parametrize where possible.
- Never use type() when creating mock classes.
- Use module-level constants with "_" prefix.

- Name test functions clearly after the behavior: `test_inhibits_when_fips_enabled` not `test_fips_1`.
- Look at existing tests in `repos/system_upgrade/common/actors/` for project conventions before writing new ones.

## Running tests

See `skills/leapp-test-runner/` for full commands. Quick single-actor run:

```bash
ACTOR=<actor_name> make dev_test_no_lint
```

