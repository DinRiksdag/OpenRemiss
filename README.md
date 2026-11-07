# OpenRemiss

OpenRemiss builds a dataset of Swedish government consultations (*remisser*),
invited organisations, and responses using [g0v.se's open data](https://g0v.se).

It imports consultation metadata and document links, extracts invitation lists
from PDFs, and cleans organisation names. The results are stored in SQLite
to help explore which organisations are invited and which respond.

- [Setup, usage, and development](docs/getting_started.md)
- [Data model and SQL examples](docs/data_structure.md)

Organisation names are inferred from attachment names and PDF contents;
they may require manual review.

Created at a Civic Tech hackathon in Göteborg in September 2018 by
[Emil Hemdal](https://github.com/emilhem), Albin, and
[Pierre Mesure](https://github.com/PierreMesure). Licensed under [AGPLv3](LICENSE).
