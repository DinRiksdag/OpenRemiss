import pytest

from models import Consultee, Document
from service.cleaner import Cleaner, clean_records
from service.document_reviews import DOCUMENT_REVIEWS


@pytest.mark.parametrize(
    "name",
    [
        "atsec information security AB",
        "abc Sverige",
        "21 Grams",
        "2030-sekretariatet",
        "1000 möjligheter",
        "1,6 miljonerklubben",
        "4spar AB",
        "100-Gruppen",
        "7-Eleven Sverige",
        "08Gruppen",
        "1.6 miljonerklubben",
        ".SE (Stiftelsen för internetinfrastruktur)",
    ],
)
def test_cleaning_preserves_letters_and_numeric_names(name):
    assert Cleaner.light_clean(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "Svenska ILO-kommittén",
        "Flyktinggruppernas riksråd, FARR",
        "Svenskt Näringsliv, LO och PTK",
        "Sveriges Hamnar",
        "Länsstyrelsen i Västra Götalands län",
    ],
)
def test_substrings_and_cosigners_are_not_organisation_matches(name):
    assert (
        Cleaner.deep_clean(
            name, ["LO", "FAR", "Svenskt Näringsliv", "Hamnar", "Länsstyrelsen"]
        )
        == name
    )


def test_whole_names_and_faculty_qualifications_can_be_normalised():
    popular = ["Lunds universitet", "LO"]
    assert Cleaner.deep_clean("LUNDS UNIVERSITET", popular) == "Lunds universitet"
    assert (
        Cleaner.deep_clean("Lunds universitet (Juridiska fakulteten)", popular)
        == "Lunds universitet"
    )
    assert (
        Cleaner.deep_clean("LO (gemensamt med PTK)", popular)
        == "LO (gemensamt med PTK)"
    )


def test_proposal_scopes_are_removed_even_for_uncommon_organisations():
    assert (
        Cleaner.deep_clean(
            "Bokföringsnämnden (förslaget att inordna uppgifterna i Finansinspektionen)",
            [],
        )
        == "Bokföringsnämnden"
    )
    assert (
        Cleaner.deep_clean(
            "En nämnd (förslaget att samordna arbetet (avsnitt 2.5))", []
        )
        == "En nämnd"
    )
    assert Cleaner.deep_clean("En förening (RF)", []) == "En förening (RF)"


def test_reviewed_response_organisation_is_preserved_by_cleaning():
    review = next(r for r in DOCUMENT_REVIEWS.values() if r.get("organisation"))
    document = Document(
        remiss_url=review["page_url"],
        url=review["url"],
        name=review["label"],
        kind="answer",
    )
    clean_records([document], [])
    assert document.organisation == review["organisation"]
    assert document.name == review["label"]


def test_shared_words_in_response_labels_are_preserved():
    documents = [
        Document(
            remiss_url="https://example.org/r",
            url=f"https://example.org/d{i}",
            name=name,
            kind="answer",
        )
        for i, name in enumerate(
            ["Lunds kommun", "Malmö kommun", "Kiruna kommun", "Åmåls kommun"]
        )
    ]
    consultees = [
        Consultee(
            remiss_url=documents[0].remiss_url,
            document_url="https://example.org/list",
            name="atsec information security AB",
        )
    ]
    clean_records(documents, consultees)
    assert [d.organisation for d in documents] == [d.name for d in documents]
    assert consultees[0].cleaned_name == "atsec information security AB"


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Region Dalarna - bilaga", "Region Dalarna"),
        ("Region Dalarna - bIlaga", "Region Dalarna"),
        ("Umeå kommun Bilaga", "Umeå kommun"),
        ("Västra Götalandsregionen - bilaga", "Västra Götalandsregionen"),
        ("Försvarsmakten_bilaga", "Försvarsmakten"),
        ("Stockholms universitet Bilaga 1", "Stockholms universitet"),
        ("Nynäshamns kommun_bilaga C", "Nynäshamns kommun"),
        ("Försvarsmakten Underbilaga 1.2", "Försvarsmakten"),
        (
            "The Walt Disney Company Nordic AB, bilaga",
            "The Walt Disney Company Nordic AB",
        ),
        ("Region Jönköpings län inkl.bilaga", "Region Jönköpings län"),
        ("Gotlands kommun - bilaga till remissvar", "Gotlands kommun"),
        ("Försvarsmaktens remissvar", "Försvarsmakten"),
        ("Försäkringskassans remissvar", "Försäkringskassan"),
        ("Svenskt Näringsliv - kompletterande remissvar", "Svenskt Näringsliv"),
        ("Euroclear Sweden remissvar", "Euroclear Sweden"),
        ("Remissvar Finansinspektionen", "Finansinspektionen"),
    ],
)
def test_response_attachment_labels_are_not_part_of_organisation_names(label, expected):
    assert (
        Cleaner.response_name(
            label, ["Försvarsmakten", "Försäkringskassan", "Finansinspektionen"]
        )
        == expected
    )


@pytest.mark.parametrize(
    "label",
    [
        "Saco bilaga Akavia",
        "Saco bilaga SRAT",
        "Bilaga PM A konsekvensutredning RS",
        "Remissvar angående nya regler för cybersäkerhet",
        "Remissvar från LO och PTK",
        "Försvarsmaktens forskningsinstitut",
    ],
)
def test_response_cleanup_preserves_qualified_labels_and_unknown_topics(label):
    assert Cleaner.response_name(label, ["Saco", "LO", "Försvarsmakten"]) == label


def test_response_genitive_requires_an_independently_known_name():
    assert Cleaner.response_name("Okändas remissvar") == "Okändas"
    assert Cleaner.response_name("Saco-S remissvar", ["Saco-S", "Saco"]) == "Saco-S"


def test_pipeline_cleans_reported_response_labels_and_preserves_raw_names():
    labels = [
        "Region Dalarna - bilaga",
        "Umeå kommun Bilaga",
        "Västra Götalandsregionen - bilaga",
        "Försvarsmaktens remissvar",
        "Försvarsmakten",
    ]
    documents = [
        Document(
            remiss_url="https://example.org/r",
            url=f"https://example.org/{i}",
            name=label,
            kind="answer",
        )
        for i, label in enumerate(labels)
    ]
    clean_records(documents, [])
    assert [d.name for d in documents] == labels
    assert [d.organisation for d in documents] == [
        "Region Dalarna",
        "Umeå kommun",
        "Västra Götalandsregionen",
        "Försvarsmakten",
        "Försvarsmakten",
    ]


@pytest.mark.parametrize(
    "label,expected",
    [
        ("001 Riksdagens ombudsmän", "Riksdagens ombudsmän"),
        ("002 Göta hovrätt", "Göta hovrätt"),
        ("005HelsingborgsTingsrätt", "HelsingborgsTingsrätt"),
        ("017a Ekobrottsmyndigheten rättelse", "Ekobrottsmyndigheten rättelse"),
        ("004GöteborgsTingsrätt", "Göteborgs tingsrätt"),
        ("008FörvaltningsrätteniStockholm.docx", "Förvaltningsrätten i Stockholm"),
        ("01 Allmänna reklamationsnämnden", "Allmänna reklamationsnämnden"),
        (
            "020Myndighetenförsamhällsskyddochberedskap",
            "Myndigheten för samhällsskydd och beredskap",
        ),
        ("2017-01344-ARM_svar_nr_009_Datainspektionen-", "Datainspektionen"),
        ("2017-01344-ARM_svar_nr_017_Försäkringskassan-", "Försäkringskassan"),
        ("2017-01344-ARM_svar_nr_022_IFAU-", "IFAU"),
        ("2017-01344-ARM_svar_nr_025_Kammarrätten-", "Kammarrätten"),
        (
            "2017-01344-ARM_svar_nr_032_Lantbrukarnas Riksförbund-",
            "Lantbrukarnas Riksförbund",
        ),
        ("2017-01344-ARM_svar_nr_036_Migrationsverket-", "Migrationsverket"),
        (
            "2017-01344-ARM_svar_nr_037_Myndigheten för tillväxtpolitiska utvärderingar och analyser-",
            "Myndigheten för tillväxtpolitiska utvärderingar och analyser",
        ),
        ("2017-01344-ARM_svar_nr_040_Regelrådet-", "Regelrådet"),
        ("2017-01344-ARM_svar_nr_041_Riksdagens ombudsmän-", "Riksdagens ombudsmän"),
        ("33.1_SACO_Akademikerförundet SSR", "Akademikerförundet SSR"),
        ("33.2_SACO_Sveriges Ingenjörer", "Sveriges Ingenjörer"),
        ("33.3_SACO_Sveriges läkarförbund", "Sveriges läkarförbund"),
        ("33.4_SACO_Sveriges Psykologförbund", "Sveriges Psykologförbund"),
        ("34 (1) Kungsbacka kommun", "Kungsbacka kommun"),
        ("34 (2) Kungsbacka kommun", "Kungsbacka kommun"),
        ("34.1 Huddinge kommun bilaga", "Huddinge kommun"),
        ("34.1_Statstjänstemannaförbundet", "Statstjänstemannaförbundet"),
        ("39.1 Stockholms läns landsting", "Stockholms läns landsting"),
        ("A-2014-1359-A_svar_nr_030_Linnéuniversitetet", "Linnéuniversitetet"),
        ("A2016 02514-A_svar_nr_006_Pensionsmyndigheten", "Pensionsmyndigheten"),
        ("A. Aramachi (utom listan)", "A. Aramachi"),
        ("A2013-01165-ARM_svar_nr_002_Malmö tingsrätt-", "Malmö tingsrätt"),
        ("A2013-01165-ARM_svar_nr_003_Arbetsdomstolen-", "Arbetsdomstolen"),
        ("A2013-01165-ARM_svar_nr_004_SIEPS-", "SIEPS"),
        ("A2013-01165-ARM_svar_nr_005_Migrationsverket-", "Migrationsverket"),
    ],
)
def test_reported_response_numbering_and_filename_forms(label, expected):
    known = [
        "Göteborgs tingsrätt",
        "Förvaltningsrätten i Stockholm",
        "Myndigheten för samhällsskydd och beredskap",
    ]
    assert Cleaner.deep_clean(Cleaner.response_name(label, known), known) == expected


def test_compact_names_require_unique_full_name_matches():
    assert (
        Cleaner.deep_clean("GöteborgsTingsrätt", ["Göteborgs tingsrätt"])
        == "Göteborgs tingsrätt"
    )
    assert Cleaner.deep_clean("ABC", ["A BC", "AB C"]) == "ABC"
    assert Cleaner.deep_clean("LOochPTK", ["LO", "PTK"]) == "LOochPTK"
    assert Cleaner.response_name("08Gruppen", ["Försvarsmakten"]) == "08Gruppen"
    assert (
        Cleaner.response_name("1.6 miljonerklubben", ["Försvarsmakten"])
        == "1.6 miljonerklubben"
    )


@pytest.mark.parametrize(
    "label,expected",
    [
        (
            "Statens musikverks remissvar En kulturkanon för Sverige",
            "Statens musikverk",
        ),
        (
            "Polismyndighetens remissvar Tillfälligt återinförande av taxameterdispens",
            "Polismyndigheten",
        ),
        ("Stora Enso Remisssvar", "Stora Enso"),
        ("Trafikanalys Beslut om remissvar", "Trafikanalys"),
        ("Kvinnofronten-remissvar-SOU-2023-97", "Kvinnofronten"),
        ("Huddinge kommun Remissyttrande", "Huddinge kommun"),
        ("Remissvar Högskolan i Gävle", "Högskolan i Gävle"),
        (
            "Remissvar Svensk Scenkonst angående Vissa statliga insatser",
            "Svensk Scenkonst",
        ),
        ("Remissvar Lunds tingsrätt_Ju 2025.01048", "Lunds tingsrätt"),
        ("Remissvar Ekobrottsmyndigheten (NISU)", "Ekobrottsmyndigheten"),
        ("Karlskrona kommun svar remiss", "Karlskrona kommun"),
        ("Lunds kommun beslut remiss", "Lunds kommun"),
        ("Lunds kommun missiv remiss", "Lunds kommun"),
        ("Lunds kommun remiss", "Lunds kommun"),
        ("AIPPI utanf remissl", "AIPPI"),
        ("FICPI Sweden utanför remissl", "FICPI Sweden"),
        ("Utom remisslistan_Skytten Fastighets AB", "Skytten Fastighets AB"),
        (
            "Bilaga: Remissvaret från Myndigheten för samhällsskydd och beredskap",
            "Myndigheten för samhällsskydd och beredskap",
        ),
    ],
)
def test_response_metadata_found_by_remiss_query(label, expected):
    assert Cleaner.response_name(label, [expected]) == expected


def test_response_topics_require_a_complete_known_sender():
    for label in [
        "Remissvar angående nya regler för cybersäkerhet",
        "Remissvar från LO och PTK",
        "Föreningen LO och PTK remissvar om skatter",
        "Remissvar Institutet för språk och folkminnen och Riksarkivet",
    ]:
        assert (
            Cleaner.response_name(
                label, ["LO", "PTK", "Institutet för språk och folkminnen"]
            )
            == label
        )


def test_uncommon_independent_labels_can_identify_response_senders():
    labels = [f"Vanlig organisation {i}" for i in range(300)] + [
        "Högskolan i Gävle",
        "Remissvar Högskolan i Gävle",
        "Polismyndigheten",
        "Polismyndighetens",
        "Polismyndighetens remissvar om trafik",
    ]
    documents = [
        Document(
            remiss_url="https://example.org/r",
            url=f"https://example.org/{i}",
            name=label,
            kind="answer",
        )
        for i, label in enumerate(labels)
    ]
    clean_records(documents, [])
    assert documents[301].organisation == "Högskolan i Gävle"
    assert documents[-1].organisation == "Polismyndigheten"
    assert [d.name for d in documents] == labels


def test_former_invitation_label_and_topic_are_not_part_of_response_name():
    assert (
        Cleaner.response_name(
            "Myndigheten för säkerhet och integritetsskydd (Säkerhets- och integritetsskyddsnämnden i remisslistan)",
            ["Myndigheten för säkerhet och integritetsskydd"],
        )
        == "Myndigheten för säkerhet och integritetsskydd"
    )
    assert (
        Cleaner.response_name(
            "Region Västerbottens yttrande över remiss en hållbar bioekonomistrategi SOU 2023-84",
            ["Region Västerbotten"],
        )
        == "Region Västerbotten"
    )
