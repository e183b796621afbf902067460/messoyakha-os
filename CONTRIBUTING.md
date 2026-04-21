# Contributing Standards

A detailed overview on how to contribute.

## Philosophy

> [Writing good code is not just about **«what»** you write. It is also about **«how»** you write it.](https://pandas.pydata.org/docs/development/contributing_codebase.html#code-standards)

When implementing a feature or making any other changes it's important to prioritize delivering the best long-term solution for the project rather than rushing to complete it quickly: the **«how»** (the implementation approach) is as important as the **«what»** (the feature itself).

When writing (or reviewing) code anywhere in this project, all changes need to be thoughtful and deliberate about new abstractions, implementations, and behaviors, as every wrong decision (made in a rush or because of insufficient context) makes the codebase harder to scale and maintain and is much more difficult to change later.

Favor small, backward-compatible changes with tests. Tests need to be thorough, fast, isolated, consistently repeatable, and as simple as possible: we try to have tests both for normal behaviour and for error conditions.

As such, prefer strong primitives, powerful abstractions, general implementations and extension points that enable to build robust and maintainable codebase, over narrow solutions for specific use cases that push a particular approach to system design that hasn't yet stood the test of time.

## Getting Started With Git

We use [Git](https://git-scm.com/) for version control to allow participants to work together on the project: become familiar with cloning, creating branches, commiting and pushing changes.

Also, the project follows a branching workflow: all the steps need to be completed before you can work seamlessly between your local repository and remote origin.

### Cloning Repository

You will need your own copy of `pep` to work on the code, so you will want to clone repository to your machine:
```bash
git clone https://github.com/e183b796621afbf902067460/pep.git
```
This creates the directory `pep` and connect your local repository to the upstream `pep` repository.

<!-- general-rule:1 -->
> [!NOTE]
> After cloning repository always prefer running scripts (or commands) from root of the repository.

### Branching Rules

Your local `master` branch must always reflect the current state of `pep` repository: it's a defaul branch in this repository, ensure it's up-to-date with the main repository (assuming you're already in the `master` branch):
```bash
git pull master --ff-only
```

<!-- general-rule:2 -->
Then, create a branch for making your changes, for example for bugfix:
```bash
git checkout -b bug/short-branch-name
```
This changes your working branch from `master` to the `bug/short-branch-name` branch: keep any changes in this branch specific to one bug or feature so it is clear what the branch brings to `pep`.

#### Branch Naming Rules

| Prefix            | When To Use                               |
| ----------------- | ----------------------------------------- |
| `feature`         | Enhancement, new functionality            |
| `bug`             | Bug fix                                   |
| `doc`             | Additions (or updates) to documentation   |
| `test`            | Additions (or updates) to tests           |
| `build`           | Updates to the build process (or CI)      |
| `type`            | Additions (or updates) to type annotations|
| `clean`           | Any cleanup                               |

### Changing Codebase

Then once you have made code changes, you can see all the changes you've currently made by running:
```bash
git status
```

Let's say you've created (or modified) `path/to/file-to-be-added-or-changed.*` file, to add those changes, run:
```bash
git add path/to/file-to-be-added-or-changed.*
```

Finally, commit your changes to your local repository with an explanatory commit message, for example:
```bash
git commit -m "Some explanatory commit message goes here"
```

### Pushing Changes

When you want your changes to appear publicly, push a new local branch that doesn't yet exist on the remote:
```bash
git push --set-upstream origin bug/short-branch-name
```

Now your code is not yet a part of the `pep` project: your request then goes to the repository maintainers, and they will review the code. Based on the review you get on your changes, you will probably need to make some adjustments to the code.

If there are no conflicts (or they could be fixed automatically), and you can simply push your changes. Instead, you need to solve those conflicts.

## Creating a Development Environment

### Development Workflow

Before modifying any code, ensure you follow the contributing environment guidelines to set up an appropriate development environment, which requires `python` and `uv` to be installed, if so:
```bash
make sync
```
If something went wrong, you must follow all the instructions provided.

### Code Quality

Additionally, CI will run code formatting checks using `pre-commit`: any warnings from these checks will cause the CI to fail; therefore, it is helpful to run the check yourself before submitting code.

#### Installing `pre-commit` Hooks

This can be done by running:
```bash
uv run pre-commit install --install-hooks
```
Now all of the styling checks will be run each time you commit changes.

#### Running `pre-commit` Hooks

<!-- general-rule:3 -->
Always run all code formatting checks, not specific linter:
```bash
make pre-commit
```

<!-- general-rule:4 -->
Always format and check files with `pre-commit` after writing or editing them to format, lint, and autofix code! This is mandatory and must never be skipped — code quality checks are essential for all contributions! Do this for every file created (or modified): generating any warnings will cause the check to fail — fix any failures until all checks passed!

## Code Standards

<!-- general-rule:5 -->
`pep` codebase contains many current examples, and we strongly encourage copying the style of existing code when working on new task (whether it's a feature, bug, or test)!

### Writing Code

In an effort to adhere to the [self-documenting code](https://en.wikipedia.org/wiki/Self-documenting_code) approach and to improve the chances of your changes being accepted, the following are fundamental guidelines to be considered:

<!-- general-rule:6 -->
- imports at top of file (module-scoped), never use deferred imports (function-scoped);

<!-- general-rule:7 -->
- imports must follow the full package (or library, or module) name convention (don't use aliases, import fully qualified names);

<!-- general-rule:8 -->
- decouple dependencies onto multiple smaller classes (and functions as well) that operate on a smaller domain doing «one thing» only (making them easier to name, understand and reuse: keep your changes as simple as possible);

<!-- general-rule:9 -->
- use descriptive, readable names for variables, functions and classes (avoid shortening variable names, e.g. use `version` instead of `v`);

<!-- general-rule:10 -->
- only add strategic comments that explain non-obvious logic or provide additional context.

There are certain rules for naming enforcements:

<!-- general-rule:11 -->
- use single word names by default for new locals, params, functions, and classes;

<!-- general-rule:12 -->
- multi-word names are allowed only when a single word would be unclear or ambiguous;

<!-- general-rule:13 -->
- do not introduce new compounds (whether it is `CamelCase`, or `snake_case`) when a short single word alternative is clear;

<!-- general-rule:14 -->
- before finishing edits, review touched (or created) lines and shorten newly introduced identifiers where possible.

### Testing Code

<!-- general-rule:15 -->
`pep` is serious about testing and strongly encourages contributors to embrace [TDD](https://en.wikipedia.org/wiki/Test-driven_development). So, before actually writing any code, you should write your tests. However, it's always worth considering additional use cases and writing corresponding tests. We recommend striving to ensure code you add or change within `pep` is covered by a test.

All tests must go into `tests` subdirectory of the specific package (or module), and `tests` subdirectoty structure must mirrors source code. Test suite will run automatically on CI: any warnings from these tests will cause the CI to fail, therefore:

<!-- general-rule:16 -->
- ensure you have appropriate tests;

<!-- general-rule:17 -->
- tests require deterministic behavior;

<!-- general-rule:18 -->
- prefer running specific tests over running the entire test suite.

<!-- general-rule:19 -->
Do this for every test created (or modified): fix any failures until all tests passed!

Adding tests is one of the most common requests after code is pushed to `pep`. Therefore, it is worth getting in the habit of writing tests ahead of time so this is never an issue.

### Reviewing Code

<!-- general-rule:20 -->
Do self-review and verify that every change is related to the task (instead, remove any unrelated changes).

### Documenting Code

The code itself is a documentation, which is almost should look like it was written in plain English. This is described in detail in the relevant section of the appropriate sub-core's contribution guidelines.

## Contributing Policy

All contributions, bug fixes, documentation improvements, enhancements, and ideas are welcome! We ask that contributors follow all contribution guidelines when participating in project development: this contributing policy applies to any contribution made to project.
