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

Most existing dependency pins are retained. SQLAlchemy is constrained to 1.4
for Graphene-SQLAlchemy 2.x, Werkzeug to 2.x for Flask 2.3.2, and NumPy/pandas
to pre-major-upgrade versions for the existing parser. pikepdf is updated to
8.x for Apple Silicon wheels. `pdfminer.six` replaces `pdfminer` so it shares
OCRmyPDF's implementation rather than installing two packages into the same
namespace.

The PDF and scraping tools also need system software: Java for Tabula,
Google Chrome for Selenium, and Tesseract (with Swedish language data) and
Ghostscript for OCR. uv manages the Python dependencies only.

The former `setup.py` was a shortcut for downloading data, not a package
installer. Use `uv run python download_data.py` instead.

## Running the script

You should now be ready to run the scripts.

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

The PDF parser tests require historical files under `tmp/` that are not included
in this repository. Without those fixtures, the tests cannot pass. The root
`test.py` is an experimental data-cleaning script and is excluded from test
discovery.

## Managing dependencies

```shell
uv add <package>
uv add --dev <package>
uv lock --check
```
