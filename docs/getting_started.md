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
Reviewed types and naming exceptions are in `service/document_reviews.json`.
Invalid attachments are excluded by default; `--include-source-exceptions` includes
them with their reviewed types. Valid documents retain their reviewed classification.

### Extract invitation lists

```shell
uv run python build_remissinstans_list.py
```

Downloads invitation-list PDFs from the supplied URLs and extracts organisation
names, using OCR when needed. PDFs, extracted text, and coordinates are cached
under `tmp/`. Results are saved every 50 documents or 30 seconds, and on exit or
interruption. Completed extractions are skipped on later runs.
Non-PDF files are logged and recorded as skipped.
Document errors are logged and recorded as failed; processing continues.
Use `--reset` to re-extract completed lists using the cached PDFs and text.

### Clean organisation names

```shell
uv run python clean_data.py
```

Cleans names inferred from response attachment names and invitation lists.
Matching is heuristic and may require manual review.

For an optional reference comparison, put [Myndighetsdata's](https://github.com/civictechsweden/myndighetsdata) `scb.json`, `esv.json`,
and `wd.json` in a directory as `myndighetsdata-{source}.json`, then run:

```shell
uv run python audit_names.py --reference-dir path/to/references
```

The audit writes review suggestions under `tmp/quality_audit/matching/` without
changing names. Optional `wikidata-municipalities.csv` and
`wikidata-organisations.csv` snapshots use semicolon-separated `item`, `label`,
`number`, and `alias` columns. Aliases and fuzzy matches always require review.

Commands show progress with tqdm. Detailed logs and separate warning/error logs
are saved under `tmp/logs/`.

See [the datasets and examples](data_structure.md) for analysing the results.

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
Known parser bugs use strict xfail; `--runxfail` exposes their failing assertions.
Use `-m 'quality and not source_exception'` to omit known source metadata errors.

Install and run the hooks:

```shell
uv run pre-commit install
uv run pre-commit run --all-files
```

CI runs Ruff, ty, and pytest on pushes and pull requests.

Add dependencies with `uv add <package>` or `uv add --dev <package>`,
and commit the updated `pyproject.toml` and `uv.lock`.
