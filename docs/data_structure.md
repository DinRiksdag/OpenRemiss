# Datasets

OpenRemiss stores three Parquet files under `data/`. Records are validated
with the Pydantic models in `models.py` and read or written through pandas.

| File | Contents | Key |
| --- | --- | --- |
| `remisser.parquet` | URL, title, publication date, department, diary number | `url` |
| `documents.parquet` | Attachment URL and name, kind, responding organisation, extraction status and error | `remiss_url`, `url` |
| `consultees.parquet` | Invited organisation names and cleaned names | `remiss_url`, `document_url` identifies the invitation list |

Document kinds are `answer`, `consultee_list`, and `other`. Invitation lists
have an extraction status of `pending`, `complete`, or `failed`; other
documents have no extraction status. Original names remain available alongside
cleaned names.

## Analyse with pandas

```python
import pandas as pd

remisser = pd.read_parquet("data/remisser.parquet")
documents = pd.read_parquet("data/documents.parquet")
consultees = pd.read_parquet("data/consultees.parquet")

# Organisations submitting the most response documents
answers = documents[documents["kind"] == "answer"]
print(answers["organisation"].value_counts().head(20))

# Responses with consultation titles and departments
responses = answers.merge(
    remisser[["url", "title", "issuer"]],
    left_on="remiss_url",
    right_on="url",
    suffixes=("", "_remiss"),
)
```
