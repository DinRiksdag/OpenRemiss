# Getting started

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run
from the repository root:

```shell
uv sync --locked
```

The project uses Python 3.15. Dependencies are declared in `pyproject.toml`
and locked in `uv.lock`.

PDF extraction uses LiteParse with bundled Tesseract. The Swedish OCR model is
downloaded and cached on first use; no additional system tools are required.

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
names, using OCR when needed. PDFs, extracted text, and coordinates are cached
under `tmp/`. Results are saved every 50 documents or 30 seconds, and on exit or
interruption. Completed extractions are skipped on later runs.
Non-PDF files are logged and recorded as skipped.

### Clean organisation names

```shell
uv run python clean_data.py
```

Cleans names inferred from response attachment names and invitation lists.
Matching is heuristic and may require manual review.

Commands show progress with tqdm. Detailed logs and separate warning/error logs
are saved under `tmp/logs/`.

See [the datasets and pandas examples](data_structure.md) for analysing the results.

## Development

```shell
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest -ra
```

Use `uv run ruff check --fix .` and `uv run ruff format .` to apply fixes.
Run the real-PDF quality suite manually (excluded from the default run and CI):

```shell
uv run pytest -m quality --durations=0 -ra
```

Cases in `test/quality/cases.json` check list sizes and/or exact names. PDFs are
downloaded into `tmp/` when missing; each run repeats extraction and reports timings.

Install and run the hooks:

```shell
uv run pre-commit install
uv run pre-commit run --all-files
```

CI runs Ruff, ty, and pytest on pushes and pull requests.

Add dependencies with `uv add <package>` or `uv add --dev <package>`,
and commit the updated `pyproject.toml` and `uv.lock`.
