---
name: leapp-unit-tests
description: Write or fix unit tests for leapp-repository actors and shared libraries. Covers test placement, mocking patterns, and project conventions.
---

# Write Leapp Repository Unit Tests

Create unit tests for the leapp-repository project following established conventions and best practices.

## Usage

```
/write-leapp-tests <library_or_actor_path>
```

Example:
```
/write-leapp-tests repos/system_upgrade/common/libraries/mylib/
```

## Instructions

You are creating unit tests for the leapp-repository project. Follow these guidelines strictly:

### 1. Test File Structure

**For libraries:**
- Create tests in `<library_path>/tests/` directory
- Name test files as `test_<module_name>.py`
- Example: `repos/system_upgrade/common/libraries/dnflibs/tests/test_dnfconfig.py`

**For actors:**
- Create tests in `<actor_path>/tests/` directory
- Name test files following convention in existing actor tests
- Example: `repos/system_upgrade/common/actors/scanfips/tests/test_scanfips.py`

### 2. Required Imports

```python
import pytest  # Only if using parametrize or fixtures

from leapp.libraries.common.testutils import CurrentActorMocked, logger_mocked
from leapp.libraries.stdlib import api, CalledProcessError

# Import the module being tested
# Import any required models
```

### 3. Testing Style - Follow Petr Stodulka's Patterns

**Use pytest.mark.parametrize extensively:**
```python
@pytest.mark.parametrize('input_value,expected', [
    ('value1', 'expected1'),
    ('value2', 'expected2'),
])
def test_function(input_value, expected):
    result = module.function(input_value)
    assert result == expected
```

**Create proper mock classes (NEVER use type()):**
```python
class MockDNFBase:
    def __init__(self):
        self.conf = MockDNFConf()
        self._fill_sack_called = False
    
    def fill_sack(self):
        self._fill_sack_called = True
```

**Use module-level constants with _ prefix:**
```python
_SAMPLE_DATA = [
    'line1',
    'line2',
]
```

### 4. Mocking Best Practices

**Use logger_mocked() from testutils (NOT lambda functions):**
```python
from leapp.libraries.common.testutils import logger_mocked

monkeypatch.setattr(api, 'current_logger', logger_mocked())
```

**Mock CalledProcessError correctly (3 required parameters):**
```python
from leapp.libraries.stdlib import CalledProcessError

err = CalledProcessError(
    'Error message',
    ['command', 'arg1', 'arg2'],
    {'stdout': 'output', 'stderr': 'error', 'exit_code': 1}
)
```

**Use CurrentActorMocked for actor context:**
```python
from leapp.libraries.common.testutils import CurrentActorMocked

monkeypatch.setattr(api, 'current_actor', CurrentActorMocked(src_ver='8.10', dst_ver='9.3'))
```

**Create proper nested mock classes:**
```python
class MockDNF:
    class conf:
        Conf = MockDNFConf
    
    Base = MockDNFBase
    
    class exceptions:
        RepoError = RepoError
```

### 5. Command Validation

**Use EXACT equality checks (NOT 'in' operator):**
```python
# WRONG - weak validation
assert '--disableplugin' in context.last_cmd
assert 'plugin1' in context.last_cmd

# CORRECT - exact validation, split for readability
expected_cmd = [
    'dnf', 'config-manager', '--dump',
    '--disableplugin', 'plugin1',
    '--disableplugin', 'plugin2'
]
assert context.last_cmd == expected_cmd
```

### 6. Python 3.6+ Compatibility

**REQUIRED - code must work on Python 3.6:**
- ✓ Use `super().__init__()` (Python 3 style)
- ✗ NO f-strings (use `.format()` or `%`)
- ✗ NO walrus operator `:=`
- ✗ NO positional-only parameters `/`
- ✗ NO dataclasses
- ✗ NO typing.Literal, typing.TypedDict

**Example:**
```python
# WRONG - f-string not supported in Python 3.6
message = f"Error: {error}"

# CORRECT - use format
message = "Error: {}".format(error)
```

### 7. Mock Context Pattern

**Create reusable mock contexts:**
```python
class MockContext:
    def __init__(self, stdout=None, should_raise=None):
        self.stdout = stdout or []
        self.should_raise = should_raise
        self.commands = []
    
    @property
    def last_cmd(self):
        return self.commands[-1] if self.commands else None
    
    def call(self, cmd, split=False):
        self.commands.append(cmd)
        if self.should_raise:
            raise self.should_raise
        if split:
            return {'stdout': self.stdout}
        return None
```

### 8. Line Length and Formatting

**Follow flake8 rules (max 119 characters):**
```python
# WRONG - line too long
assert context.last_cmd == ['dnf', 'config-manager', '--save', '--setopt', 'exclude=pkg1', '--disableplugin', 'plugin1', '--disableplugin', 'plugin2']

# CORRECT - split across multiple lines
expected_cmd = [
    'dnf', 'config-manager', '--save',
    '--setopt', 'exclude=pkg1',
    '--disableplugin', 'plugin1',
    '--disableplugin', 'plugin2'
]
assert context.last_cmd == expected_cmd
```

### 9. Testing the Tests

After creating tests, verify they work correctly:

**Step 1: Register repositories (if not done):**
```bash
./tut/bin/python -c "from leapp.snactor import main; main()" repo find --path repos
```

**Step 2: Run the tests:**
```bash
# Run specific test file
./tut/bin/python -m pytest path/to/test_file.py -v

# Run all tests in directory
./tut/bin/python -m pytest path/to/tests/ -v

# Quick mode (no verbose)
./tut/bin/python -m pytest path/to/tests/ -q
```

**Step 3: Run flake8 (PEP 8 compliance):**
```bash
./tut/bin/python -m flake8 path/to/tests/
# Should output nothing or "0" if using --count
```

**Step 4: Run pylint (code quality):**
```bash
./tut/bin/python -m pylint path/to/tests/
# Target: 10.00/10 score
```

**Step 5: Run isort (import sorting):**
```bash
./tut/bin/python -m isort --check path/to/tests/
# Should output nothing if correct
```

**All-in-one verification:**
```bash
echo "=== Tests ===" && \
./tut/bin/python -m pytest path/to/tests/ -q && \
echo && echo "=== Flake8 ===" && \
./tut/bin/python -m flake8 path/to/tests/ && echo "PASSED" && \
echo && echo "=== Pylint ===" && \
./tut/bin/python -m pylint path/to/tests/ 2>&1 | grep "rated at"
```

### 10. Common Pitfalls to Avoid

**❌ DON'T:**
- Use `type()` for dynamic class creation
- Use lambda functions for logger mocking
- Use weak command validation with `in` operator
- Use Python 3.7+ features (f-strings, walrus, etc.)
- Import pytest if not using parametrize/fixtures
- Create CalledProcessError with wrong number of arguments
- Write lines longer than 119 characters
- Use old-style `super(ClassName, self)` calls
- Import modules at function/method level (except MagicMock pattern)

**✅ DO:**
- Create proper mock classes with `__init__`
- Use `logger_mocked()` from testutils
- Use exact command equality checks
- Ensure Python 3.6+ compatibility
- Remove unused imports
- Use proper `super()` calls (Python 3 style)
- Split long lines for readability
- Add `@property` for computed attributes
- Use named functions instead of unnecessary lambdas

### 11. Reference Examples

See these test files for good examples:
- `repos/system_upgrade/common/libraries/dnflibs/tests/test_dnfconfig.py` - Complete pattern
- `repos/system_upgrade/common/libraries/dnflibs/tests/test_dnfmodule.py` - Nested mocks
- `repos/system_upgrade/common/libraries/dnflibs/tests/test_dnfplugin.py` - Complex mocking
- `repos/system_upgrade/common/libraries/dnflibs/tests/test_dnflibs.py` - Clean structure

### 12. Project Documentation

Refer to `/myclaude/lpr/CLAUDE.md` for:
- Project structure details
- Actor vs library testing conventions
- How to run tests with make commands
- Container testing options

## Success Criteria

Tests are complete when:
- ✓ All new tests pass (100% success rate)
- ✓ Flake8 reports 0 errors
- ✓ Pylint score is 10.00/10
- ✓ Isort check passes
- ✓ Code is Python 3.6+ compatible
- ✓ Follow Petr Stodulka's testing patterns
- ✓ Use proper mock classes (no type())
- ✓ Use exact command validation
- ✓ Use logger_mocked() from testutils
