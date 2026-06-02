# Agent Standards

A file for guiding coding agents.

<!-- agent-general-rule:1 -->
> [!IMPORTANT]
> Always answer briefly in the dialog, no need to spend tokens: everything will be clear.

## Principles

The user may not have sufficient understanding of the task he (or she) is working on, the solution space may not be well defined and the user may not be aware of the appropriate trade-offs to effectively push the agent towards an implementation approach (in fact, the **«how»**) that best meets the long-term goals of the project, this means agent should start gathering context about the feature (the **«what»**) at hand:

- asking the user questions about the scope of the task;
- requesting a more fleshed out plan in a `PLAN.md` file (or any other).

We can represent user-agent interactions as a repeated classic example of _game theory (3, 3)_, where equilibrium is achieved when both decide to cooperate fairly: the agent's cooperation strategy is to develop and maintain a code according to high standards, and the user's cooperation strategy is to use agents, therefore making them better and better, so such cooperation will incentivize both increasing the likelihood of our project thriving.

There are some behavioral principles to reduce common agent mistakes:

<!-- agent-general-rule:2 -->
- **Look Before You Leap**. State your assumptions explicitly. If something is unclear, stop. Name what's confusing, ask.

<!-- agent-general-rule:3 -->
- **Occam's Razor**. Simplicity first. Minimum code that solves the problem. Nothing speculative. No features beyond what was asked. No abstractions for single-use code. No reduntant «flexibility» or «configurability» unless requested otherwise.

<!-- agent-general-rule:4 -->
- **Measure Twice, Cut Once**. Touch only what you must. Do it with a surgical precision. Don't «improve» adjacent code, comments, or formatting. Every added (or changed) line of code must be related to the task.

In essence, agent as the first line of defense against low-quality code plays a crucial role in a game of maintaining the high standards of project development:

<!-- agent-general-rule:5 -->
- ensuring maintainability and scalability in the long-term, not short-term perspective;

<!-- agent-general-rule:6 -->
- preferring readability over optimization (unless benchmark is requested);

<!-- agent-general-rule:7 -->
- reviewing code contributions carefully, not quickly;

<!-- agent-general-rule:8 -->
- identifying any issues related to code-safety and code-quality;

<!-- agent-general-rule:9 -->
- encouraging your own research to fill any gaps in knowledge;

<!-- agent-general-rule:10 -->
- providing well-written documentation according to styleguides.

## Python Code Standards

### Writing Python Code

There are some general rules to apply while writing Python code:

<!-- py-rule:1 -->
- follow «[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)»;

<!-- py-rule:2 -->
- boolean variables (or parameters) must be started with `is_*` prefix;

<!-- py-rule:3 -->
- no `assert` in modules, use it only in tests;

<!-- py-rule:4 -->
- no `print` in tests and modules, use `loguru` for proper output handling.

### Annotating Python Code

`pep` uses `pyrefly` to statically analyze the codebase and type hints. After making any changes you can ensure your type hints are consistent by running code formatting checks.

<!-- py-rule:5 -->
Annotate code with type hints according to [PEP 484](https://peps.python.org/pep-0484/) (don't use unnecessary `Any` annotations, the use of `cast()` is strongly discouraged) — use built-in generic types (e.g. `list[str]` instead of `typing.List[str]`), use `Union`, `Protocol`, `TypeVar`, or schema-derived types for precision — precise types catch bugs at type-check.

<!-- py-rule:6 -->
Use `TypedDict` or `pydantic` model instead of `dict[str, Any]` when structure is known — it enables static type checking, eliminates `cast()` calls, provides runtime validation, and self-documenting expected structure.

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

To run a specific test, for example in `somewhere-in-messoyakha/tests/unit/test_dummy.py`:
```bash
uv run pytest somewhere-in-messoyakha/tests/unit/test_dummy.py
```

<!-- py-rule:12 -->
> [!IMPORTANT]
> Always run scripts (or commands) from root of the repository, not specific core (e.g. `make pre-commit` must always run from root).

### Running Python Code

To run a specific script, for example located in `somewhere-in-messoyakha/script_dummy.py`:
```bash
uv run somewhere-in-messoyakha/script_dummy.py
```

### Documenting Python Code

We use docstrings to document the code! Update (or add) all relevant documentation only after code change is final:

<!-- py-rule:13 -->
- follow «[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)» docstring conventions when documenting code ([PEP 257](https://peps.python.org/pep-0257/) is part of it);

<!-- py-rule:14 -->
- only add examples in docstrings for complex functionality;

<!-- py-rule:15 -->
- only add docstrings in tests when they provide additional context.
