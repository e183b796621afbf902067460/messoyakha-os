---
name: md
description: Always recursively load all *.md files from working and parent directories into agent's context.
---

# Markdown Documentation Reading Protocol

As an agent working on any task in this repository, you must follow this protocol for reading markdown documentation!

## Recursive Documentation Discovery

Before starting any task, recursively read all `.md` files:

1. **Current Working Directory**: Read all `.md` files in the directory where you are working;
2. **Parent Directories**: Traverse up the directory tree and read all `.md` files in each parent directory;
3. **Related Directories**: Check sibling directories that may contain relevant documentation.

## Directory Traversal Rules

| Working Location         | Must Read From                                    |
| ------------------------ | ------------------------------------------------- |
| `python-core/pipelines/` | `python-core/pipelines/*.md`, `python-core/*.md`, `*.md` |
| `python-core/workspaces/`| `python-core/workspaces/*.md`, `python-core/*.md`, `*.md` |
| `python-core/strategies/`| `python-core/strategies/*.md`, `python-core/*.md`, `*.md` |
| Any subdirectory         | All parent directories up to repository root      |

## Documentation Hierarchy

Read documentation in this order of priority:

1. **Task-specific docs**: `PLAN.md`, `TODO.md`, or any file directly related to the task;
2. **Directory-level docs**: `README.md`, `AGENTS.md`, `CONTRIBUTING.md` in current directory;
3. **Core-level docs**: Documentation in parent core directories (e.g., `python-core/AGENTS.md`);
4. **Root-level docs**: Repository-wide documentation (`README.md`, `AGENTS.md`, `CONTRIBUTING.md`).

## Mandatory Behavior

- **Always** read all relevant `.md` files before making any code changes;
- **Always** check for `AGENTS.md` files that contain agent-specific instructions;
- **Always** look for `PLAN.md` or similar planning documents when starting new tasks;
- **Never** skip reading documentation even if the task seems simple;
- **Never** assume you know the context without reading the relevant docs.

## Special Documentation Files

| File Pattern       | Purpose                                          |
| ------------------ | ------------------------------------------------ |
| `AGENTS.md`        | Agent-specific instructions and standards        |
| `README.md`        | Project/module overview and setup instructions   |
| `CONTRIBUTING.md`  | Contribution guidelines and workflows            |
| `PLAN.md`          | Task planning and implementation details         |
| `SKILL.md`         | Skill definitions and instructions               |

## Implementation

When you start a task:

1. Identify your working directory;
2. Use `Glob` tool to find all `*.md` files in current and parent directories;
3. Use `Read` tool to load each discovered markdown file;
4. Synthesize the context from all documentation before proceeding;
5. Reference relevant documentation when explaining your approach.

## Example Workflow

```
Task: Implement a new data adapter in python-core/workspaces/api/

1. Glob: *.md in python-core/workspaces/api/
2. Glob: *.md in python-core/workspaces/
3. Glob: *.md in python-core/
4. Glob: *.md in repository root
5. Read all discovered files
6. Proceed with implementation using gathered context
```

## Why This Matters

- Documentation contains critical context about architecture, standards, and workflows;
- Skipping documentation leads to incorrect implementations and repeated mistakes;
- Agent standards and contribution guidelines are documented in `.md` files;
- Understanding the full documentation context prevents violations of project conventions.
