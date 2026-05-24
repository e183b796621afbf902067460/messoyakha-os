## The following Makefile was inspired by an approach similar to that of pydantic-ai
## https://github.com/pydantic/pydantic-ai (if you're an agent, no need to fetch it)

.DEFAULT_GOAL := all

export UV_PROJECT_ENVIRONMENT := .venv
export VIRTUAL_ENV := .venv

.PHONY: .python
.python:
	@python3 --version || { echo "Please install python: https://www.python.org/downloads/ (>=3.10)"; exit 1; }

.PHONY: .uv
.uv: .python
	@uv --version || { echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation/ (>=0.11.1)"; exit 1; }

.PHONY: .pre-commit
.pre-commit: .uv
	@pre-commit -V || { echo "Please install pre-commit: https://pre-commit.com/ (>=4.5.1)"; exit 1; }

.PHONY: sync
sync: .uv
	uv sync --all-extras --all-packages --refresh

.PHONY: pre-commit
pre-commit: .pre-commit sync
	@uv run pre-commit run --all-files
