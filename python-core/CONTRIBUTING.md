# Python Contributing Standards

A detailed overview on how to contribute in `python-core/`.

## Python Code Standards

### Writing Python Code

There are some general rules to apply while writing code in `python-core/`:

<!-- py-rule:1 -->
- follow «[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)»;

<!-- py-rule:2 -->
- boolean variables (or parameters) must be started with `is_*` prefix;

<!-- py-rule:3 -->
- no `assert` in modules, use it only in tests;

<!-- py-rule:4 -->
- no `print` in tests and modules, use `loguru` for proper output handling.

### Annotating Python Code

`pep` uses `pyrefly` to statically analyze the codebase nad type hints. After making any change you can ensure your type hints are consistent by running code formatting checks.

<!-- py-rule:5 -->
Annotate code with type hints according to [PEP 484](https://peps.python.org/pep-0484/) (don't use unnecessary `Any` annotations, the use of `cast()` is strongly discouraged) — use built-in generic types (e.g. `list[str]` instead of `typing.List[str]`), use `Union`, `Protocol`, `TypeVar`, or schema-derived types for precision — precise types catch bugs at type-check.

<!-- py-rule:6 -->
Use `TypedDict` or `pydnatic` model instead of `dict[str, Any]` when structure is known — it enables static type checking, eliminates `cast()` calls, provides runtime validation, and self-documenting expected structure.

<!-- py-rule:7 -->
When `Any` is unavoidable due to external constraints, document expected structure in docstrings.

### Testing Python Code

For running tests, we use `pytest`. Tests always live in `tests/` directory and mirrors source code, so:

<!-- py-rule:8 -->
- every file that includes tests has a `test__*` prefix;

<!-- py-rule:10 -->
- wrap tests in classes named with `Test*` prefix;

<!-- py-rule:11 -->
- tests must be named `def test_*` and only take arguments that are either fixtures or parameters;

<!-- py-rule:12 -->
- use a bare `assert` for truth-testing;

To run a specific test, for example in `python-core/somewhere-in-python-core/tests/unit/test_dummy.py`:
```bash
uv run --directory python-core/ pytest somewhere-in-python-core/tests/unit/test_dummy.py
```

<!-- py-rule:12 -->
> [!IMPORTANT]
> Always run scripts (or commands) from root of the repository, not specific core.

### Running Python Code

To run a specific script, for example located in `python-core/somewhere-in-python-core/script_dummy.py`:
```bash
uv run --directory python-core/ somewhere-in-python-core/script_dummy.py
```

### Documenting Python Code

We use docstrings to document the code! Update (or add) all relevant documentation only after code change is final:

<!-- py-rule:13 -->
- follow «[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)» docstring conventions for all functions and classes ([PEP 257](https://peps.python.org/pep-0257/) is part of it);

<!-- py-rule:14 -->
- only add examples in docstrings for complex functionality;

<!-- py-rule:15 -->
- only add docstrings in tests when they provide additional context.

## Add New Strategy

1. Create directory in `python-core/strategies`, for example `my-awesome-strategy`.

2. Create `pyproject.toml` in `python-core/strategies/my-awesome-strategy` with following structure:

    ```toml
    [project]
    name = "pep-my-awesome-strategy"
    version = "0.0.1"
    description = "My awesome description."
    readme = "README.md"

    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"

    [tool.hatch.build.targets.wheel]
    packages = ["src"]

    [tool.hatch.build.force-include]
    "src" = "pep_my_awesome_strategy"
    ```

3. Update following sections in your `python-core/pyproject.toml`:

    a. Update `[project]` dependencies:
    ```toml
    [project]
    ...
    dependencies = [
        ...,
        "pep-my-awesome-strategy"
    ]
    ```

    b. Update `[tool.uv.sources]`:
    ```toml
    [tool.uv.sources]
    pep-my-awesome-strategy = { path = "strategies/my-awesome-strategy", editable = true }
    ```

    c. Update `[tool.ruff.lint.isort]` known-first-party:
    ```toml
    [tool.ruff.lint.isort]
    known-first-party = [..., "pep_my_awesome_strategy"]
    ```

    d. Update `[tool.pyrefly]` search-path:
    ```toml
    [tool.pyrefly]
    search-path = [..., "strategies/my-awesome-strategy"]
    ```

4. Then run:
    ```bash
    make sync
    ```

After that you can do any imports from your strategy codebase by `pep_my_awesome_strategy` name.
