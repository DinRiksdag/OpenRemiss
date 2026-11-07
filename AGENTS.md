# Working on OpenRemiss

Read `README.md` and `docs/getting_started.md` for context and setup.

- Use uv for Python commands and dependencies: `uv sync --locked`.
- Before finishing, run `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run ty check`, and `uv run pytest -ra`.
- Format code with `uv run ruff format .`; add tests for behaviour changes.
- Keep documentation concise and focused on the current project.
- After parser changes, run `uv run pytest -m quality --durations=0 -ra`.
- Add evaluated PDFs to `test/quality/cases.json` with `id`, `url`, `pdf_sha256`,
  and `expected_count` and/or `expected_names` (in document order).
  Review expectations against the PDF; never copy extraction mistakes to make
  a test pass. The manual suite downloads missing PDFs into the URL-hash cache
  under `tmp/` and re-extracts them without reusing cached text.
