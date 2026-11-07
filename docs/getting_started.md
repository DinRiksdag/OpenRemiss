# Getting started

## Installing Python and the dependencies with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run the following from the repository root:

```shell
uv sync --locked
```

uv installs Python 3.11 if needed and creates a local `.venv` with the locked
dependencies, including pytest. Dependencies are declared in `pyproject.toml`;
commit `uv.lock` whenever they change. Python is temporarily limited to 3.11
while the legacy dependencies are modernised.

Most existing dependency pins are retained. SQLAlchemy stays on 1.4 to preserve
the existing ORM APIs, and NumPy/pandas stay on pre-major-upgrade versions for
the existing parser. pikepdf is updated to
8.x for Apple Silicon wheels. `pdfminer.six` replaces `pdfminer` so it shares
OCRmyPDF's implementation rather than installing two packages into the same
namespace.

The PDF and scraping tools also need system software: Java for Tabula,
Google Chrome for Selenium, and Tesseract (with Swedish language data) and
Ghostscript for OCR. uv manages the Python dependencies only.

The former `setup.py` was a shortcut for downloading data, not a package
installer. Use `uv run python download_data.py` instead.

## Running the script

Run the following command-line scripts from the repository root. They save data
to `database/database.db`, which you can query directly with SQL.

### Downloading the main lists

Start with `download_data.py`:

```shell
uv run python download_data.py
```

This will download a list of all the remiss processes and a list of all the associated files. It will also try to categorize these files as well as possible as:
- a *remisslista*, a list of consultees published by the government
- a *remissvar*, an answer from an organisation sent back to the government
- another document

### Downloading and rebuilding the list of consultees

```shell
uv run python build_remissinstans_list.py
```

This will download all the list of consultees and try to parse the content. Unfortunately, every government department has its own file structure 🤦🏼‍ so results may vary and the script can still be improved. For example. Finansdepartementet publishes most of its lists as scanned PDFs...

### Cleaning the data

```shell
uv run python clean_data.py
```

Unfortunately, we have to use file names to identify the senders of the answers and these are rarely just the organisation names. In addition to all the numbers, appendices, typos, one organisation can also be named differently.

The same goes for the consultees extracted from the lists.

This scripts is an attempt at cleaning these organisation names. It doesn't do a perfect job and it can even be wrong or lose some useful information (ex: *Lunds universitet (Juridiska fakulteten)* -> *Lunds universitet*).

This is why we don't overwrite the information but save it in new fields.

## Running tests

```shell
uv run pytest
```

Parser helper tests run without downloaded files. The historical PDF tests use
files under `tmp/` that are not included in this repository; each test skips if
its fixture is missing. Restoring the fixtures enables those tests automatically.
The root `test.py` is an experimental data-cleaning script and is excluded from
test discovery.

## Code quality and pre-commit hooks

```shell
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest -ra
```

Ruff checks basic Python errors and formatting. ty checks the database models,
services, pipeline scripts, and tests configured in `pyproject.toml`; the standalone
experiments `test.py` and `convertdiarier.py` are outside its scope.
Use `uv run ruff check --fix .` and `uv run ruff format .` to apply fixes.

Install the Git hooks once per checkout:

```shell
uv run pre-commit install
uv run pre-commit run --all-files
```

The hooks run Ruff lint, Ruff formatting, and ty. Keep their pinned versions
aligned with `uv.lock` when upgrading the tools. GitHub Actions runs those same
checks plus pytest on pushes and pull requests.

## Managing dependencies

```shell
uv add <package>
uv add --dev <package>
uv lock --check
```
