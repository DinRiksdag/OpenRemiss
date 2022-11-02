# Getting started

## Installing Python and the dependencies

To run this program, you will need to [install Python 3 and pip](https://realpython.com/installing-python/).

When this is done, you can just run the following to install all the dependencies.

```shell
pip3 install -r requirements.txt
```

## Running the script

You should now be ready to run the scripts.

### Downloading the main lists

Start with `download_data.py`:

```shell
python3 download_data.py
```

This will download a list of all the remiss processes and a list of all the associated files. It will also try to categorize these files as well as possible as:
- a *remisslista*, a list of consultees published by the government
- a *remissvar*, an answer from an organisation sent back to the government
- another document

### Downloading and rebuilding the list of consultees

```shell
python3 build_remissinstans_list.py
```

This will download all the list of consultees and try to parse the content. Unfortunately, every government department has its own file structure 🤦🏼‍ so results may vary and the script can still be improved. For example. Finansdepartementet publishes most of its lists as scanned PDFs...

### Cleaning the data

```shell
python3 clean_data.py
```

Unfortunately, we have to use file names to identify the senders of the answers and these are rarely just the organisation names. In addition to all the numbers, appendices, typos, one organisation can also be named differently.

The same goes for the consultees extracted from the lists.

This scripts is an attempt at cleaning these organisation names. It doesn't do a perfect job and it can even be wrong or lose some useful information (ex: *Lunds universitet (Juridiska fakulteten)* -> *Lunds universitet*).

This is why we don't overwrite the information but save it in new fields.
