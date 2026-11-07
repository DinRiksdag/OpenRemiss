import csv
import json

from audit_names import read_references
from service.name_matching import NameMatcher


def test_reference_loading_preserves_courts_and_reused_names(tmp_path):
    scb = {
        "Domstolsverket": {"org_nr": "202100-2742"},
        "Attunda tingsrätt": {"org_nr": "202100-2742"},
        "Statskontoret": {"org_nr": "202100-5026"},
        "STATSKONTORET": {"org_nr": "202100-0852", "end": "2025-12-31"},
    }
    wd = {"Domstolsverket": {"id": "Q100", "org_nr": "2021002742"}}
    for source, data in [("scb", scb), ("esv", {}), ("wd", wd)]:
        (tmp_path / f"myndighetsdata-{source}.json").write_text(json.dumps(data))
    for kind in ["municipalities", "organisations"]:
        with (tmp_path / f"wikidata-{kind}.csv").open("w", newline="") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(["item", "label", "number", "alias"])
            if kind == "organisations":
                writer.writerow(
                    [
                        "http://www.wikidata.org/entity/Q100",
                        "Domstolsverket",
                        "2021002742",
                        "DV",
                    ]
                )

    references = read_references(tmp_path)
    assert len(references) == 4
    matcher = NameMatcher(references)
    host = matcher.resolve("Domstolsverket")
    court = matcher.resolve("Attunda tingsrätt")
    assert host["status"] == court["status"] == "exact_label"
    assert host["candidates"][0]["entity_id"] == "Q100"
    assert court["candidates"][0]["entity_id"] != "Q100"
    assert matcher.resolve("DV")["status"] == "alias_review"
    assert matcher.resolve("Statskontoret", 2024)["status"] == "ambiguous_label"
    assert matcher.resolve("Statskontoret", 2026)["status"] == "exact_label"
