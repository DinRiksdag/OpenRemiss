"""Conservative, opt-in reference matching. Suggestions never change source records."""

from collections import defaultdict
from typing import TypedDict

from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from service.cleaner import name_key


class MatchCandidate(TypedDict):
    entity_id: str
    name: str
    source: str
    score: float


class MatchResult(TypedDict):
    status: str
    candidates: list[MatchCandidate]


class ReferenceName(BaseModel):
    entity_id: str
    name: str
    source: str
    aliases: list[str] = Field(default_factory=list)
    organisation_number: str | None = None
    start: int | None = None
    end: int | None = None


class NameMatcher:
    def __init__(self, references: list[ReferenceName]):
        self.references = {record.entity_id: record for record in references}
        self.labels = defaultdict(set)
        self.aliases = defaultdict(set)
        for record in references:
            self.labels[name_key(record.name)].add(record.entity_id)
            for alias in record.aliases:
                self.aliases[name_key(alias)].add(record.entity_id)
        self.choices = sorted(set(self.labels) | set(self.aliases))

    def eligible(self, entity_id: str, year: int | None) -> bool:
        reference = self.references[entity_id]
        return year is None or (
            (reference.start is None or reference.start <= year)
            and (reference.end is None or reference.end >= year)
        )

    def resolve(self, name: str, year: int | None = None) -> MatchResult:
        key = name_key(name)
        exact = sorted(
            entity_id
            for entity_id in self.labels.get(key, ())
            if self.eligible(entity_id, year)
        )
        reference_matches = [
            entity_id
            for entity_id in exact
            if self.references[entity_id].source != "recurring"
        ]
        if reference_matches:
            return self.result(
                "exact_label" if len(reference_matches) == 1 else "ambiguous_label",
                [(entity_id, 100.0) for entity_id in reference_matches],
            )
        aliases = sorted(
            entity_id
            for entity_id in self.aliases.get(key, ())
            if self.eligible(entity_id, year)
        )
        if aliases:
            return self.result(
                "alias_review" if len(aliases) == 1 else "ambiguous_alias",
                [(entity_id, 100.0) for entity_id in aliases],
            )
        if exact:
            return self.result(
                "recurring_label", [(entity_id, 100.0) for entity_id in exact]
            )
        if len(key.replace(" ", "")) <= 5:
            return self.result("unmatched", [])

        # Rank whole strings. Token/subset scorers can turn different organisations
        # sharing a geographic or generic word into convincing-looking matches.
        scores = {}
        for choice, score, _ in process.extract(
            key, self.choices, scorer=fuzz.ratio, score_cutoff=90, limit=25
        ):
            for entity_id in self.labels.get(choice, set()) | self.aliases.get(
                choice, set()
            ):
                if self.eligible(entity_id, year):
                    scores[entity_id] = max(scores.get(entity_id, 0), score)
        ranked = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))[:3]
        if not ranked:
            return self.result("unmatched", [])
        margin = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else 100.0
        status = "fuzzy_review" if margin >= 5 else "ambiguous_fuzzy"
        return self.result(status, ranked)

    def result(self, status, ranked) -> MatchResult:
        return {
            "status": status,
            "candidates": [
                {
                    "entity_id": entity_id,
                    "name": self.references[entity_id].name,
                    "source": self.references[entity_id].source,
                    "score": round(score, 2),
                }
                for entity_id, score in ranked
            ],
        }
