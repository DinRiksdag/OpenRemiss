# Getting started

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run
from the repository root:

```shell
uv sync --locked
```

The project uses Python 3.11. Dependencies are declared in `pyproject.toml`
and locked in `uv.lock`.

PDF extraction requires Java for Tabula, Tesseract with Swedish language data,
and Ghostscript for OCR.

## Run the pipeline

### Import consultations

```shell
uv run python download_data.py
```

Imports consultation metadata and attachment links from [g0v.se](https://g0v.se/remisser.json)
into Parquet files under `data/`. Each run refreshes consultations in the feed.
Removed attachments and their derived data are deleted; unchanged documents
retain extracted names. Consultations outside the feed are left untouched.

### Extract invitation lists

```shell
uv run python build_remissinstans_list.py
```

Downloads invitation-list PDFs from the supplied URLs and extracts organisation
names, using OCR when needed. Downloaded and OCR files are cached under `tmp/`.
Completed extractions are saved as the command progresses and skipped on later runs.
Non-PDF files are logged and recorded as skipped.

### Clean organisation names

```shell
uv run python clean_data.py
```

Cleans names inferred from response attachment names and invitation lists.
Matching is heuristic and may require manual review.

See [the datasets and pandas examples](data_structure.md) for analysing the results.

## Development

```shell
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest -ra
```

Use `uv run ruff check --fix .` and `uv run ruff format .` to apply fixes.
Historical PDF tests skip when their fixtures under `tmp/` are missing.

Install and run the hooks:

```shell
uv run pre-commit install
uv run pre-commit run --all-files
```

CI runs Ruff, ty, and pytest on pushes and pull requests.

Add dependencies with `uv add <package>` or `uv add --dev <package>`,
and commit the updated `pyproject.toml` and `uv.lock`.
