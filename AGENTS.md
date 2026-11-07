# Working on OpenRemiss

Read `README.md` and `docs/getting_started.md` for context and setup.

- Use uv for Python commands and dependencies: `uv sync --locked`.
- Before finishing, run `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run ty check`, and `uv run pytest -ra`.
- Format code with `uv run ruff format .`; add tests for behaviour changes.
- Keep documentation concise and focused on the current project.
