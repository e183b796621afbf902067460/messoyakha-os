# Agent Standards

A file for guiding coding agents.

## Philosophy

> [Writing good code is not just about **«what»** you write. It is also about **«how»** you write it.](https://pandas.pydata.org/docs/development/contributing_codebase.html#code-standards)

When implementing a feature or making any other changes it's important to prioritize delivering the best long-term solution for the project rather than rushing to complete it quickly: the **«how»** (the implementation approach) is as important as the **«what»** (the feature itself).

When writing (or reviewing) code anywhere in this project, all changes need to be thoughtful and deliberate about new abstractions, implementations, and behaviors, as every wrong decision (made in a rush or because of insufficient context) makes the codebase harder to scale and maintain and is much more difficult to change later.

Favor small, backward-compatible changes with tests. Tests need to be thorough, fast, isolated, consistently repeatable, and as simple as possible: we try to have tests both for normal behaviour and for error conditions.

As such, prefer strong primitives, powerful abstractions, general implementations and extension points that enable to build robust and maintainable codebase, over narrow solutions for specific use cases that push a particular approach to system design that hasn't yet stood the test of time.

## Principles

We can represent user-agent interactions as a repeated classic example of _game theory (3, 3)_, where equilibrium is achieved when both decide to cooperate fairly: the agent's cooperation strategy is to develop and maintain a code according to high standards, and the user's cooperation strategy is to use agents, therefore making them better and better, so such cooperation will incentivize both increasing the likelihood of our project thriving.

There are some behavioral principles to reduce common agent mistakes:

<!-- agent-general-rule:1 -->
- **Look Before You Leap**. State your assumptions explicitly. If something is unclear, stop. Name what's confusing, ask.

<!-- agent-general-rule:2 -->
- **Occam's Razor**. Simplicity first. Minimum code that solves the problem. Nothing speculative. No features beyond what was asked. No abstractions for single-use code. No reduntant «flexibility» or «configurability» unless requested otherwise.

<!-- agent-general-rule:3 -->
- **Measure Twice, Cut Once**. Touch only what you must. Do it with a surgical precision. Don't «improve» adjacent code, comments, or formatting. Every added (or changed) line of code must be related to the task.

In essence, agent as the first line of defense against low-quality code plays a crucial role in a game of maintaining the high standards of project development:

<!-- agent-general-rule:4 -->
- ensuring maintainability and scalability in the long-term, not short-term perspective;

<!-- agent-general-rule:5 -->
- preferring readability over optimization (unless benchmark is requested);

<!-- agent-general-rule:6 -->
- reviewing code contributions carefully, not quickly;

<!-- agent-general-rule:7 -->
- identifying any issues related to code-safety and code-quality;

<!-- agent-general-rule:8 -->
- encouraging your own research to fill any gaps in knowledge;

<!-- agent-general-rule:9 -->
- providing well-written documentation according to styleguides.

## Python Code Standards

### Setting Python Development Environment

Before modifying/running any code, ensure you follow the contributing environment guidelines to set up an appropriate development environment, which requires `python` and `uv` to be installed, if so run in the root of `messoyakha-os`:
```bash
make sync
```
If something went wrong, you must follow all the instructions provided.

### Running Python Code

To run a specific script, for example located in `somewhere-in-project/script_to_run.py`, run following command from root of `messoyakha-os` (use `uv` to automatically create/manage virtual environment):
```bash
uv run somewhere-in-project/script_to_run.py
```

<!-- running-python-code-rule:1 [!IMPORTANT] -->
Always run scripts (or commands) from root of the repository, not specific core (e.g. `make pre-commit` must always run from root).

### Writing Python Code

<!-- writing-python-code-rule:1 [!IMPORTANT] -->
`messoyakha-os` codebase contains many current examples, and we strongly encourage copying the style of existing code when working on new task (whether it's a feature, bug, or test)!

In an effort to adhere to the [self-documenting code](https://en.wikipedia.org/wiki/Self-documenting_code) approach and to improve the chances of your changes being accepted, the following are fundamental guidelines to be considered:

<!-- writing-python-code-rule:2 -->
- imports must follow the full package (or library, or module) name convention (don't use aliases, import fully qualified names);

<!-- writing-python-code-rule:3 -->
- decouple dependencies onto multiple smaller classes (and functions as well) that operate on a smaller domain doing «one thing» only (making them easier to name, understand and reuse: keep your changes as simple as possible);

<!-- writing-python-code-rule:4 -->
- use descriptive, readable names for variables, functions and classes (avoid shortening variable names, e.g. use `version` instead of `v`); boolean variables (or parameters) must be started with `is_*` prefix;

<!-- writing-python-code-rule:5 -->
- use single word names by default for new locals, params, functions, and classes; multi-word names are allowed only when a single word would be unclear or ambiguous and provides better descriptiveness and readability;

<!-- writing-python-code-rule:6 -->
- only add strategic comments that explain non-obvious logic or provide additional context;

There are certain general rules to follow too:

<!-- writing-python-code-general-rule:1 -->
- follow «[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)»;

<!-- writing-python-code-general-rule:2 -->
- no `assert` in modules, use it only in tests;

<!-- writing-python-code-general-rule:3 -->
- no `print` in tests and modules, use `loguru` for proper output handling.

### Annotating Python Code

`messoyakha-os` uses `pyrefly` to statically analyze the codebase and type hints. After making any changes you can ensure your type hints are consistent by running code formatting checks.

<!-- annotating-python-code-rule:1 -->
Annotate code with type hints according to [PEP 484](https://peps.python.org/pep-0484/) (don't use unnecessary `Any` annotations, the use of `cast()` is strongly discouraged) — use built-in generic types (e.g. `list[str]` instead of `typing.List[str]`) — precise types catch bugs at type-check.

<!-- annotating-python-code-rule:2 -->
Use `TypedDict` or `pydantic` model instead of `dict[str, Any]` when structure is known — it enables static type checking, eliminates `cast()` calls, provides runtime validation, and self-documenting expected structure.

<!-- annotating-python-code-rule:3 -->
When `Any` is unavoidable due to external constraints, document expected structure in docstrings.

### Linting Python Code

Additionally, CI will run code formatting checks using `pre-commit`: any warnings from these checks will cause the CI to fail; therefore, it is helpful to run the check yourself before submitting code.

<!-- linting-python-code-rule:1 [!IMPORTANT] -->
Always run all code formatting checks using `make` utility, not specific linter using `uv`:
```bash
make pre-commit
```

<!-- linting-python-code-rule:2 -->
Always format and check files with `make pre-commit` command after writing or editing them to format, lint, and autofix code! This is mandatory and must never be skipped — code quality checks are essential for all contributions! Do this for every file created (or modified): generating any warnings will cause the check to fail — fix any failures until all checks passed!

### Documenting Python Code

<!-- documenting-python-code-rule:1 -->
The code itself is a documentation, which is almost should look like it was written in plain English.

We use docstrings to document the code! Update (or add) all relevant documentation only after code change is final:

<!-- documenting-python-code-rule:2 -->
- follow «[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)» docstring conventions when documenting code ([PEP 257](https://peps.python.org/pep-0257/) is part of it);

<!-- documenting-python-code-rule:3 -->
- only add examples in docstrings for complex functionality;

<!-- documenting-python-code-rule:4 -->
- only add docstrings in tests when they provide additional context.

### Reviewing Code

<!-- reviewing-python-code-rule:1 -->
Do self-review and verify that every change is related to the task (instead, remove any unrelated changes).
