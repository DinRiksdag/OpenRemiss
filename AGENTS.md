# Working on OpenRemiss

OpenRemiss collects Swedish government consultations and responses. Read
`README.md` and `docs/getting_started.md` for context and setup.

- Use uv for Python commands and dependencies. Start with `uv sync --locked`.
- Run `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run ty check`, and `uv run pytest -ra` before finishing changes.
- Use `uv run ruff check --fix .` and `uv run ruff format .` to fix lint
  and formatting. Keep changes focused and update documentation when needed.
- Add tests for behaviour changes. Historical PDF tests skip when their
  fixtures under `tmp/` are missing; do not replace their expected results
  just to make them pass.
- Set up hooks with `uv run pre-commit install`. Check all tracked files with
  `uv run pre-commit run --all-files`.
