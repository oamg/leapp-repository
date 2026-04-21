# Making development tools work

The Leapp framework uses dynamic import mechanisms to load entities from repositories at runtime. While this keeps import paths concise, the non-standard setup often causes development tools—such as language servers and type checkers—to behave unreliably or fail entirely.

Fortunately, some tools, such as [Pyright](https://github.com/microsoft/pyright) and [Pylance](https://github.com/microsoft/pylance-release), can be tricked to work using standard Python type stub files. Scripts are used to generate type stubs reflecting the runtime module layout and tools can then be configured to prioritize these stubs over real source files. To get started follow the setup instructions:

  1. Configure your tool of choice to use the `typings` directory in the root of the project as the type stub directory.
For example to configure this in Pyright, add the following to `pyrightconfig.json`:
```json
  "stubPath": "./typings",
  "reportMissingTypeStubs": false,
```

```{note}
A `pyrightconfig.json` with reasonable configuration for the project is already included in the repository.
```

  2. Install `mypy` (used for stub generation): `pip install mypy`.
  3. Generate the stubs by running the `make stubgen` command. Note that the generated stubs are static, i.e. regeneration is required to reflect new changes in source files.
