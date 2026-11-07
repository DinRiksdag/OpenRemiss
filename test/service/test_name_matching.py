from service.name_matching import NameMatcher, ReferenceName


def reference(entity_id, name, **kwargs):
    return ReferenceName(entity_id=entity_id, name=name, source="registry", **kwargs)


def test_full_labels_match_but_substrings_and_short_typos_do_not():
    matcher = NameMatcher([reference("lo", "LO"), reference("far", "FAR")])
    assert matcher.resolve("lo")["status"] == "exact_label"
    for name in ["Svenska ILO-kommittén", "FARR", "LO och PTK"]:
        assert matcher.resolve(name)["status"] == "unmatched"


def test_courts_with_a_shared_organisation_number_remain_distinct():
    matcher = NameMatcher(
        [
            reference("dv", "Domstolsverket", organisation_number="2021002742"),
            reference("court", "Attunda tingsrätt", organisation_number="2021002742"),
        ]
    )
    assert matcher.resolve("Attunda tingsrätt")["candidates"][0]["entity_id"] == "court"


def test_reused_name_is_ambiguous_for_historical_documents():
    matcher = NameMatcher(
        [
            reference("old", "Statskontoret", end=2025),
            reference("new", "Statskontoret", start=1998),
        ]
    )
    assert matcher.resolve("Statskontoret", 2024)["status"] == "ambiguous_label"
    match = matcher.resolve("Statskontoret", 2026)
    assert match["status"] == "exact_label"
    assert match["candidates"][0]["entity_id"] == "new"


def test_aliases_are_review_candidates_even_when_unique():
    matcher = NameMatcher(
        [reference("skolverket", "Skolverket", aliases=["Lärarnas ansvarsnämnd"])]
    )
    assert matcher.resolve("Lärarnas ansvarsnämnd")["status"] == "alias_review"


def test_ocr_typo_is_suggested_without_becoming_a_validated_match():
    matcher = NameMatcher(
        [
            reference("transport", "Transportstyrelsen"),
            reference("traffic", "Trafikverket"),
        ]
    )
    result = matcher.resolve("Transpottstyrelsen")
    assert result["status"] == "fuzzy_review"
    assert result["candidates"][0]["entity_id"] == "transport"


def test_near_identical_place_names_are_ambiguous_not_automatically_matched():
    matcher = NameMatcher(
        [
            reference("a", "Länsstyrelsen i Norrbottens län"),
            reference("b", "Länsstyrelsen i Västerbottens län"),
        ]
    )
    result = matcher.resolve("Länsstyrelsen i Österbottens län")
    assert result["status"] in ("fuzzy_review", "ambiguous_fuzzy", "unmatched")
    assert result["status"] != "exact_label"


def test_recurring_strings_are_not_claimed_as_authority_validation():
    matcher = NameMatcher(
        [
            ReferenceName(
                entity_id="observed", name="Some organisation", source="recurring"
            )
        ]
    )
    assert matcher.resolve("Some organisation")["status"] == "recurring_label"


def test_different_court_can_have_a_high_fuzzy_score_without_validating_identity():
    matcher = NameMatcher([reference("lower", "Patent- och marknadsdomstolen")])
    result = matcher.resolve("Patent- och marknadsöverdomstolen")
    assert result["status"] == "fuzzy_review"
    assert result["candidates"][0]["score"] > 93
