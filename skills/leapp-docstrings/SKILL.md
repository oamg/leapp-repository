# Writing Docstrings

Write and update docstrings of functions and modules in leapp-repository project
following best practices and conventions.

## Format style
Use **Sphinx/reStructuredText** format for all docstrings to ensure proper documentation generation.

## Type notation (`:type:` / `:rtype:` / `:vartype:`)
Use **capitalized `typing`-module generics**, not lowercase PEP 585 builtins. The
type strings double as real type annotations (which must run on **Python 3.6**,
where `list[str]` / `collections.abc.Iterable[str]` are not subscriptable at
runtime) and must resolve under **older Sphinx/intersphinx** versions.

- `List[X]`, `Dict[K, V]`, `Set[X]`, `FrozenSet[X]`, `Tuple[X, Y]`
- `Optional[X]`, `Union[X, Y]`, `Iterable[X]`, `Iterator[X]`, `Sequence[X]`, `Mapping[K, V]`
- A bare container is still capitalized: `:rtype: List` (not `list`).
- Do **not** write `list[X]`, `set[X]`, `tuple[X, Y]`, or `collections.abc.Iterable[X]`.

```python
    :type repoids: Iterable[str]
    :type copy_files: List[CopyFile]
    :rtype: Tuple[Set[str], Set[str]]
```

## Basic Structure

```python
def function_name(param1, param2):
    """
    Brief one-line description.

    Optional longer description providing more context about what the
    function does, when to use it, and any important behavior details.

    :param param1: Description of first parameter
    :type param1: Type of first parameter
    :param param2: Description of second parameter
    :type param2: Type of second parameter
    :returns: Description of return value
    :rtype: Return type
    :raises ExceptionType: When and why this exception is raised
    """
```

## Exception Documentation Strategy

Use a **reference-based approach** to maintain single source of truth and avoid documentation duplication:

**1. When calling public functions:**
- Use `.. seealso::` to reference the called function
- Put the reference body on a new line for readability
- Don't duplicate the called function's exception documentation

```python
def high_level_function():
    """
    Perform a high-level operation.

    .. seealso::
        :func:`low_level_public_function` for exceptions raised during processing.
    """
    return low_level_public_function()
```

**2. When calling private functions (starting with `_`):**
- Document the private function's exceptions **directly** in the caller's docstring
- Treat private functions as implementation details (not part of public API)
- Use `:raises:` clauses for each exception the private function raises

```python
def public_function():
    """
    Perform an operation using internal implementation.

    :raises DNFExecutionError: When the DNF command fails to execute.
    :raises DNFUpgradeTransactionError: When the transaction encounters an error.
    """
    return _private_helper()  # Private - document its exceptions above
```

**3. Mixed scenarios (calling both public and private):**
- Document private function exceptions with `:raises:`
- Reference public functions with `.. seealso::`

```python
def complex_function():
    """
    Perform a complex operation with multiple dependencies.

    :raises DNFExecutionError: When the DNF command fails to execute.
    :raises DNFUpgradeTransactionError: When the transaction fails.

    .. seealso::
        :func:`dnfconfig.exclude_leapp_rpms` - For DNF configuration exceptions
    """
    _private_transaction()  # Exceptions documented above
    dnfconfig.exclude_leapp_rpms()  # Exceptions referenced in seealso
```

**4. When a function directly raises exceptions:**
- Always document with `:raises:` clause
- Include context about when/why the exception is raised

```python
def install_plugin(target_path):
    """
    Install the DNF plugin to the target path.

    :param target_path: Destination directory for the plugin
    :raises DNFPluginInstallError: When the plugin file cannot be copied.
    :raises KeyError: When the target system version is not supported.
    """
    try:
        shutil.copy2(plugin_file, target_path)
    except EnvironmentError:
        raise DNFPluginInstallError("Failed to install plugin")
```

## Benefits of Reference-Based Documentation

- **Maintainability**: Change exceptions in one place, not throughout the call chain
- **Single source of truth**: Each exception documented only where it originates
- **Clear API boundaries**: Public vs private distinction is evident
- **Discoverability**: Developers can follow references to understand error paths

## Example: Good Documentation

See these functions as reference examples:
- `repos/system_upgrade/common/libraries/dnflibs/dnfconfig.py:exclude_leapp_rpms()` - Complete exception documentation
- `repos/system_upgrade/common/libraries/dnflibs/dnfmodule.py:get_modules()` - Has `:raises:` clause
- `repos/system_upgrade/common/libraries/dnflibs/dnfplugin.py:perform_transaction_install()` - Mixed strategy
