# Omnislash

A personal retail trading framework for developing and backtesting various strategies (and their combinations, too) to build a robust portfolio of uncorrelated returns.

# Configuration

First of all to configure project correctly need to do next steps:

- Clone current repository:
```
git clone https://github.com/e183b796621afbf902067460/omnislash.git
```

- Get into the project folder:
```
cd omnislash/
```

- Set environment variables in [.env](https://github.com/e183b796621afbf902067460/omnislash/blob/master/src/settings.py).

The repository uses `pre-commit` for code quality (formatting, linting etc.), install hooks with:
```bash
uv run pre-commit install --install-hooks
```

- https://pandas.pydata.org/docs/dev/development/contributing.html#getting-started-with-git;
- https://github.com/pandas-dev/pandas/blob/main/AGENTS.md#pull-requests-summary.

### Running Code

Run scripts from root of the repository.

To run a specific script, for example in `src/entrypoints/dummy.py`:
```bash
uv run -s src/entrypoints/dummy.py
```

# Docker

- Run docker compose (`sudo`):
```
docker-compose up -d --build
```
