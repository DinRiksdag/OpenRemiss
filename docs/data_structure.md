# Datasets

OpenRemiss stores three Parquet files under `data/`. Records are validated
with the Pydantic models in `models.py` and read or written through PyArrow.

| File | Contents | Key |
| --- | --- | --- |
| `remisser.parquet` | URL, title, publication date, department, diary number | `url` |
| `documents.parquet` | Attachment URL and name, kind, responding organisation, extraction status and error | `remiss_url`, `url` |
| `consultees.parquet` | Invited organisation names and cleaned names | `remiss_url`, `document_url` identifies the invitation list |

Document kinds are `answer`, `consultee_list`, and `other`. Invitation lists
have an extraction status of `pending`, `complete`, `failed`, or `skipped`; other
documents have no extraction status. Original names remain available alongside
cleaned names.

## Analyse the records

```python
from collections import Counter

from models import Document, Remiss
from service.storage import load

remisser = {remiss.url: remiss for remiss in load(Remiss)}
answers = [doc for doc in load(Document) if doc.kind == "answer"]

# Organisations submitting the most response documents
print(Counter(doc.organisation for doc in answers if doc.organisation).most_common(20))

# Responses with consultation titles and departments
responses = [
    (doc.organisation, remisser[doc.remiss_url].title, remisser[doc.remiss_url].issuer)
    for doc in answers
]
```
