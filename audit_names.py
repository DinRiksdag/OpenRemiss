"""Compare cleaned names with local reference snapshots without rewriting datasets."""

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import re

from tqdm import tqdm

from models import Consultee, Document, Remiss
from service.cleaner import name_key
from service.name_matching import MatchResult, NameMatcher, ReferenceName
from service.storage import DATA_DIR, load


def year(value):
    match = re.match(r"\d{4}", str(value or ""))
    return int(match[0]) if match else None


def read_references(directory):
    records = {}
    by_pair = {}

    def add(record):
        number = re.sub(r"\D", "", record.organisation_number or "") or None
        record.organisation_number = number
        pair = (name_key(record.name), number)
        existing = records.get(record.entity_id)
        if existing is None and number:
            existing = by_pair.get(pair)
        if existing:
            existing.aliases = sorted(
                set(
                    existing.aliases
                    + record.aliases
                    + (
                        [record.name]
                        if name_key(record.name) != name_key(existing.name)
                        else []
                    )
                )
            )
            existing.source = "+".join(
                sorted(set(existing.source.split("+") + record.source.split("+")))
            )
            starts = [d for d in [existing.start, record.start] if d is not None]
            ends = [d for d in [existing.end, record.end] if d is not None]
            existing.start = max(starts) if starts else None
            existing.end = min(ends) if ends else None
            if record.entity_id.startswith("Q") and not existing.entity_id.startswith(
                "Q"
            ):
                del records[existing.entity_id]
                existing.entity_id = record.entity_id
                records[existing.entity_id] = existing
            if number:
                by_pair[pair] = existing
            return
        records[record.entity_id] = record
        if number:
            by_pair[pair] = record

    for source in ["scb", "esv", "wd"]:
        path = directory / f"myndighetsdata-{source}.json"
        for name, data in json.loads(path.read_text()).items():
            number = re.sub(r"\D", "", str(data.get("org_nr", ""))) or None
            # A registration number can be shared by a host agency and many courts.
            identity = data.get("id") if source == "wd" else None
            if not identity:
                identity = (
                    "authority:"
                    + (number or "unknown")
                    + ":"
                    + sha256(name_key(name).encode()).hexdigest()[:12]
                )
            aliases = list(data.get("old_names") or []) + list(
                data.get("other_names") or []
            )
            if data.get("short_name"):
                aliases.append(data["short_name"])
            add(
                ReferenceName(
                    entity_id=str(identity),
                    name=name,
                    source="myndighetsdata_" + source,
                    organisation_number=number,
                    aliases=aliases,
                    start=year(data.get("start")),
                    end=year(data.get("end")),
                )
            )

    for kind in ["municipalities", "organisations"]:
        snapshot = directory / f"wikidata-{kind}.csv"
        if not snapshot.exists():
            continue
        with snapshot.open() as stream:
            reader = csv.DictReader(stream, delimiter=";")
            if not reader.fieldnames or "item" not in reader.fieldnames:
                raise ValueError(f"Invalid Wikidata snapshot: {kind}")
            for row in reader:
                add(
                    ReferenceName(
                        entity_id=row["item"].rsplit("/", 1)[-1],
                        name=row["label"],
                        source="wikidata_" + kind,
                        organisation_number=row.get("number") or None,
                        aliases=(row.get("alias") or row.get("aliases") or "").split(
                            "|"
                        )
                        if (row.get("alias") or row.get("aliases"))
                        else [],
                    )
                )
    return list(records.values())


def main(reference_dir: Path, output_dir: Path, data_dir: Path = DATA_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)
    consultations = {row.url: row.published_on.year for row in load(Remiss, data_dir)}
    groups = {}
    recurring = Counter()
    seen_in = defaultdict(set)

    def observe(name, consultation, url, role):
        if not name:
            return
        key = (name, consultations.get(consultation))
        row = groups.setdefault(
            key,
            {
                "name": name,
                "year": key[1],
                "respondent_rows": 0,
                "consultee_rows": 0,
                "example_url": url,
            },
        )
        row[role + "_rows"] += 1
        recurring[name] += 1
        seen_in[name].add(consultation)

    for document in load(Document, data_dir):
        if document.kind == "answer":
            observe(
                document.organisation, document.remiss_url, document.url, "respondent"
            )
    for consultee in load(Consultee, data_dir):
        observe(
            consultee.cleaned_name,
            consultee.remiss_url,
            consultee.document_url,
            "consultee",
        )

    references = read_references(reference_dir)
    reference_count = len(references)
    recurring_keys = set()
    for name, count in recurring.most_common():
        key = name_key(name)
        if (
            count >= 10
            and len(seen_in[name]) >= 3
            and len(name) <= 160
            and len(name.split()) <= 17
            and key not in recurring_keys
        ):
            recurring_keys.add(key)
            references.append(
                ReferenceName(
                    entity_id="recurring:"
                    + sha256(name_key(name).encode()).hexdigest()[:16],
                    name=name,
                    source="recurring",
                )
            )
    matcher = NameMatcher(references)
    totals = Counter()
    weighted = {role: Counter() for role in ["respondent", "consultee"]}
    fields = [
        "name",
        "year",
        "respondent_rows",
        "consultee_rows",
        "status",
        "candidate_name",
        "entity_id",
        "source",
        "score",
        "runner_up",
        "runner_up_score",
        "example_url",
    ]
    with (output_dir / "matches.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for (name, doc_year), row in tqdm(
            groups.items(), desc="Checking names", unit="name", disable=None
        ):
            if len(name) > 240 or len(name.split()) > 35:
                result: MatchResult = {"status": "extraction_review", "candidates": []}
            else:
                result = matcher.resolve(name, doc_year)
            candidates = result["candidates"]
            best = candidates[0] if candidates else {}
            runner = candidates[1] if len(candidates) > 1 else {}
            totals[result["status"]] += 1
            for role in weighted:
                weighted[role][result["status"]] += row[role + "_rows"]
            writer.writerow(
                {
                    **row,
                    "status": result["status"],
                    "candidate_name": best.get("name"),
                    "entity_id": best.get("entity_id"),
                    "source": best.get("source"),
                    "score": best.get("score"),
                    "runner_up": runner.get("name"),
                    "runner_up_score": runner.get("score"),
                }
            )
    (output_dir / "references.jsonl").write_text(
        "\n".join(r.model_dump_json() for r in references) + "\n"
    )
    summary = {
        "reference_entities": reference_count,
        "recurring_names": len(references) - reference_count,
        "name_year_pairs": len(groups),
        "statuses": dict(totals),
        "rows": {role: dict(counts) for role, counts in weighted.items()},
        "reference_files": [
            {"path": str(path), "sha256": sha256(path.read_bytes()).hexdigest()}
            for path in sorted(reference_dir.iterdir())
            if path.name
            in {
                "myndighetsdata-scb.json",
                "myndighetsdata-esv.json",
                "myndighetsdata-wd.json",
                "wikidata-municipalities.csv",
                "wikidata-organisations.csv",
            }
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("tmp/quality_audit/matching")
    )
    args = parser.parse_args()
    main(args.reference_dir, args.output_dir)
