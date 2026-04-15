# ...

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
