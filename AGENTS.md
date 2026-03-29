# Agent Standards

A file for [guiding agents](https://code.claude.com/docs/en/overview) to give persistent instructions with [files](https://agents.md/).

## Principles

> [Writing good code is not just about **«what»** you write. It is also about **«how»** you write it.](https://pandas.pydata.org/docs/development/contributing_codebase.html#code-standards)

When implementing a feature or making any other changes it's important to prioritize delivering the best long-term solution for the project rather than rushing to complete it quickly: the **«how»** (the implementation approach) is as important as the **«what»** (the feature itself).

The user may not have sufficient understanding of the task he (or she) is working on, the solution space may not be well defined and the user may not be aware of the appropriate trade-offs to effectively push the agent towards an implementation approach (in fact, the **«how»**) that best meets the long-term goals of the project, this means agent should start gathering context about the feature (the **«what»**) at hand:

- asking the user questions about the scope of the task;
- requesting a more fleshed out plan in a `PLAN.md` file (or any other).

We can represent user-agent interactions as a repeated classic example of _game theory (3, 3)_, where equilibrium is achieved when both decide to cooperate fairly: the agent's cooperation strategy is to develop and maintain a code according to high standards, and the user's cooperation strategy is to use agents, therefore making them better and better, so such cooperation will incentivize both increasing the likelihood of our project thriving.

In essence, agent as the first line of defense against low-quality code plays a crucial role in a game of maintaining the high standards of code writing:

- ensuring maintainability and scalability in the long-term, not short-term perspective;
- preferring readability over optimization (unless benchmark is requested);
- reviewing code contributions carefully, not quickly;
- identifying any issues related to code-safety and code-quality;
- encouraging your own research to fill any gaps in knowledge;
- providing well-written documentation according to styleguides.

Do not automatically do `git commit` command, only user can do it!

## Repository Structure

There are many ways to structure a project, but the best structure is one that is consistent, easy to maintain and scale! So repository has the following structure:

- shared core is stored in `src/` with following modules:
    - `schemas/` — `pydantic` models for describing all inputs/outputs;
    - `adapters/` — all the external sources (e.g. API, databases, object storages etc.);
    - `services/` — specific business logic decorated by `attrs`;
    - `entrypoints/` — `prefect` tasks and flows designed as a scripts;
    - `settings.py` — environment variables stored in `BaseSettings` class.

- tests are stored in `tests/` directory with following structure:
    - `unit/` — contains all the unit tests.

There are also `common/` and `domain/` submodules may appear in each of the `src/` modules listed above.

`uv` is used as a package manager: all the project's configuration and tool settings are stored in `pyproject.toml`.

## Coding

When writing (or reviewing) code anywhere in this project, all changes need to be thoughtful and deliberate about new abstractions, implementations, and behaviors, as every wrong decision (made in a rush or because of insufficient context) makes the codebase harder to scale and maintain and is much more difficult to change later.

In an effort to adhere to the self-documenting code approach, the following are fundamental guidelines to be considered:

- follow [«Google Python Style Guide»](https://google.github.io/styleguide/pyguide.html) styleguide for Python code (in most cases, [PEP 8](https://peps.python.org/pep-0008/) is part of it);
- prefer imports fully qualified names except of built-in modules (for instance, import `from pydantic import BaseModel` rather than `import pydantic`);
- imports at top of file (module-scoped), never use deferred imports (function-scoped);
- use descriptive, readable names for variables, functions and classes (avoid shortening variable names, e.g. use `version` instead of `v`);
- decouple dependencies onto multiple smaller classes (and functions as well) that operate on a smaller domain doing «one thing» only (making them easier to name, understand and reuse);
- annotate code with type hints according to [PEP 484](https://peps.python.org/pep-0484/) (don't use unnecessary `Any` annotations, the use of `cast` is strongly discouraged), use built-in generic types (e.g. `list[str]` instead of `typing.List[str]`);
- no `assert` in shared core modules, use it only in tests;
- no `print` in shared core and tests modules, use `loguru` for proper output handling;
- only add strategic comments that explain non-obvious logic or provide additional context;
- make sure to update the docs, docstring is sufficient enough;
- review and verify every change is related to the task (instead, remove any unrelated changes);
- copy the style of existing code samples when working on new task (whether it's a feature, bug, or test).

As such, prefer strong primitives, powerful abstractions, general implementations and extension points that enable to build robust and maintainable codebase, over narrow solutions for specific use cases that push a particular approach to system design that hasn't yet stood the test of time.

### Checking Code

Always format and check files with `pre-commit` after writing or editing them to format, lint, and autofix code! This is mandatory and must never be skipped — code quality cheks are essential for all contributions, and type hints required for all codebase including shared core and tests!

Generating any warnings will cause the check to fail, thus good style is a requirement for submitting code, so run hooks with:
```bash
uv run pre-commit run --all-files
```

Do this for every file created (or modified)! Fix any failures until all checks passed, before moving on to the next step.

## Testing

For running tests, we use `pytest`.

Favor small, backward-compatible changes with tests. Tests need to be thorough, fast, isolated, consistently repeatable, and as simple as possible: we try to have tests both for normal behaviour and for error conditions. Tests live in `tests/` directory and mirrors source code, so:

- run tests from root of the repository;
- prefer running specific tests over running the entire test suite;
- every file that includes tests has a `test_*` prefix;
- tests named `def test_*` and only take arguments that are either fixtures or parameters;
- tests require deterministic behavior.

To run a specific test by name, for example in `tests/unit/test_dummy.py`:
```bash
uv run pytest tests/unit/test_dummy.py
```

To run all tests:
```bash
uv run pytest tests/
```

Do this for every test created (or modified)! Fix any failures until all tests passed.

## Documenting

We use docstrings to document the code! Update (or add) all relevant documentation only after code change is final:

- follow [«Google Python Style Guide»](https://google.github.io/styleguide/pyguide.html) docstring conventions for all functions and classes ([PEP 257](https://peps.python.org/pep-0257/) is part of it);
- only add examples in docstrings for complex functionality;
- only add docstrings in tests when they provide additional context.
