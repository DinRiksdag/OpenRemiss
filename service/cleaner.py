from collections import Counter, defaultdict

from models import Consultee, Document


class Cleaner:
    @staticmethod
    def light_clean(text):
        return text.lstrip("0123456789abc.-_ abc ").rstrip("0123456789.-_ ")

    @staticmethod
    def deep_clean(text, popular_names):
        return next((name for name in popular_names if name in text), text)

    @staticmethod
    def is_consultee_list(filename):
        return any(
            marker in filename.casefold()
            for marker in ["remissmissiv", "remisslista", "remissinstans", "remiss av"]
        )

    @staticmethod
    def is_other_document(filename):
        return not Cleaner.is_consultee_list(filename) and any(
            marker in filename
            for marker in [
                "Remissammanställning",
                "Remissbrev",
                "Promemoria",
                "Remiss-PM",
                "Remiss av",
                "Inbjudan",
            ]
        )

    @staticmethod
    def long_substr(data):
        substr = ""
        if len(data) > 1 and len(data[0]) > 0:
            for i in range(len(data[0])):
                for j in range(len(data[0]) - i + 1):
                    if j > len(substr) and all(data[0][i : i + j] in x for x in data):
                        substr = data[0][i : i + j]
        return substr


def clean_records(documents: list[Document], consultees: list[Consultee]) -> None:
    answers = [doc for doc in documents if doc.kind == "answer"]
    groups = defaultdict(list)
    for answer in answers:
        groups[answer.remiss_url].append(answer)
    for group in groups.values():
        common = (
            Cleaner.long_substr([doc.name for doc in group]) if len(group) > 3 else ""
        )
        for answer in group:
            name = answer.name.replace(common, "") if len(common) > 3 else answer.name
            answer.organisation = Cleaner.light_clean(name)

    popular = [
        name
        for name, _ in Counter(doc.organisation for doc in answers).most_common(250)
        if name
    ]
    for answer in answers:
        answer.organisation = Cleaner.deep_clean(answer.organisation, popular)
    popular = [
        name
        for name, _ in Counter(doc.organisation for doc in answers).most_common(250)
        if name
    ]
    for consultee in consultees:
        consultee.cleaned_name = Cleaner.deep_clean(
            Cleaner.light_clean(consultee.name), popular
        )
