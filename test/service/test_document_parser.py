from service.document_parser import DocumentParser

def assert_document_parser(filepath,
        expected_result):
    assert DocumentParser.extract_list(filepath) == expected_result

def assert_document_parser_size(filepath,
        expected_size):
    assert len(DocumentParser.extract_list(filepath)) == expected_size

def test_with_pdf_1():
    # Socialdepartementet/2019
    expected_result = [
        'Autism- och Aspergerförbundet',
        'Barnombudsmannen',
        'Biobank Sverige',
        'Blekinge läns landsting',
        'Dalarnas läns landsting',
        'Datainspektionen',
        'Etikprövningsmyndigheten',
        'FUB',
        'Funktionsrätt Sverige',
        'Förvaltningsrätten i Göteborg',
        'Gotlands kommun',
        'Gävleborgs läns landsting',
        'Göteborgs universitet',
        'Hallands läns landsting',
        'Hälso- och sjukvårdens ansvarsnämnd (HSAN)',
        'Inspektionen för vård och omsorg (IVO)',
        'Judiska Centralrådet',
        'Justitiekanslern',
        'Jämtlands läns landsting',
        'Jönköpings läns landsting',
        'Kalmar läns landsting',
        'Karolinska institutet',
        'Kronobergs läns landsting',
        'Landstingens Ömsesidiga Försäkringsbolag (LÖF)',
        'Livet som gåva',
        'Lunds universitet',
        'MOD Merorgandonation',
        'Norrbottens läns landsting',
        'Njurförbundet',
        'Pensionärernas Riksorganisation (PRO)',
        'Riksdagens ombudsmän (JO)',
        'Rättsmedicinalverket',
        'Skåne läns landsting',
        'Socialstyrelsen',
        'SPF Seniorerna',
        'Statens beredning för medicinsk och social utvärdering (SBU)',
        'Statens medicinsk-etiska råd (Smer)',
        'Stockholms läns landsting',
        'Svenska kyrkan',
        'Svenska läkaresällskapet',
        'Svensk sjuksköterskeförening',
        'Sveriges Kommuner och Landsting (SKL)',
        'Sveriges kristna råd',
        'Sveriges läkarförbund',
        'Sveriges Muslimska Råd',
        'Sveriges psykologförbund',
        'Södermanlands läns landsting',
        'Södertörns tingsrätt',
        'Uppsala läns landsting',
        'Uppsala universitet',
        'Vårdförbundet',
        'Värmlands läns landsting',
        'Västerbottens läns landsting',
        'Västernorrlands läns landsting',
        'Västmanlands läns landsting',
        'Västra Götalands läns landsting',
        'Vävnadsrådet',
        'Örebro läns landsting',
        'Östergötlands läns landsting'
        ]
    assert_document_parser('tmp/1/1.pdf',
        expected_result)

def test_with_pdf_2():
    # Arbetsmarknadsdepartementet/2019
    expected_result = [
        'Alla Kvinnors Hus Karlstad',
        'Alvesta kommun',
        'Barnombudsmannen',
        'Borgholm kommun',
        'Brottsofferjouren Sverige',
        'Brottsoffermyndigheten',
        'Domstolsverket',
        'Falu kommun',
        'Freezonen (Kvinnojouren, Tjejjouren och Brottsofferjouren i Sydöstra Skåne)',
        'Förvaltningsrätten i Stockholm',
        'Förvaltningsrätten i Umeå',
        'Förvaltningsrätten i Uppsala',
        'Gällivare kommun',
        'Göteborgs kommun',
        'Habo kommun',
        'Helsingborgs kommun',
        'Härnösands kommun',
        'Hässleholms kommun',
        'Jämställdhetsmyndigheten',
        'Kammarrätten i Jönköping',
        'Klippan kommun',
        'Konkurrensverket',
        'Kungsbacka kommun',
        'Kvinnojouren – en fristad i ingenmansland',
        'Kvinnojouren Sigtuna',
        'Kvinnors nätverk',
        'Landskrona kommun',
        'Lerum kommun',
        'Länsstyrelsen i Norrbotten',
        'Länsstyrelsen i Skåne län',
        'Länsstyrelsen i Västra Götalands län',
        'Länsstyrelsen i Östergötland',
        'Malmö kommun',
        'Motala kommun',
        'Myndigheten för ungdoms- och civilsamhällesfrågor (MUCF)',
        'Män',
        'Nordmaling kommun',
        'Riksförbundet för homosexuellas, bisexuellas, transpersoners och queeras rättigheter (RFSL)',
        'Rikskriscentrum, Sveriges professionella kriscentra för män',
        'Riksorganisationen Glöm aldrig Pela och Fadime (GAPF)',
        'Riksföreningen Stödcentrum mot incest och andra sexuella övergrepp (Rise)',
        'Riksorganisationen för kvinnojourer och tjejjourer i Sverige (Roks)',
        'Ronneby kommun',
        'Rädda Barnens riksförbund',
        'Sigtuna kommun',
        'Simrishamns kommun',
        'Skyddsjouren i Ängelholm',
        'Socialstyrelsen',
        'Sollentuna kommun',
        'Sollentuna kvinnojour',
        'Stadsmissionen',
        'Stiftelsen Manscentrum i Stockholm',
        'Stockholms läns landsting',
        'Stockholms kommun',
        'Stockholms tjejjour',
        'Sunne kommun',
        'Sveriges Kommuner och Landsting',
        'Sveriges kvinnolobby',
        'Södermanlands läns landsting',
        'Talita',
        'Terrafem',
        'Tjejjouren Väst',
        'Tjejzonen',
        'Tranås kommun',
        'Trelleborgs kommun',
        'Tjejers rätt i samhället (TRIS)',
        'Ulricehamns kommun',
        'Unizon',
        'Upphandlingsmyndigheten',
        'Vara kommun',
        'Värmlands mansforum',
        'Västerbottens läns landsting',
        'Västerås kommun',
        'Västra Götalands läns landsting',
        'Åsele kommun',
        'Östersunds kommun'
        ]
    assert_document_parser('tmp/2/47.pdf',
        expected_result)

def test_with_pdf_3():
    # Kulturdepartementet/2019
    assert_document_parser_size('tmp/3/97.pdf', 90)

def test_with_pdf_162():
    # Finansdepartementet/2020
    assert_document_parser_size('tmp/162/6477.pdf', 29)

def test_with_pdf_187():
    # Utbildningsdepartementet/2020
    assert_document_parser_size('tmp/187/7444.pdf', 109)

def test_with_pdf_207():
    # Justitiedepartementet/2020
    assert_document_parser_size('tmp/207/8247.pdf', 93)

def test_with_pdf_255():
    # Infrastrukturdepartementet/2020
    assert_document_parser_size('tmp/255/10204.pdf', 13)

def test_with_pdf_305():
    # Infrastrukturdepartementet/2020
    assert_document_parser_size('tmp/305/12211.pdf', 8)

def test_with_pdf_443():
    # Socialdepartementet/2020
    assert_document_parser_size('tmp/443/18259.pdf', 77)

def test_with_pdf_452():
    # Kulturdepartementet/2020
    assert_document_parser_size('tmp/452/18629.pdf', 88)

def test_with_pdf_642():
    # Justitiedepartementet/2021
    assert_document_parser_size('tmp/642/26836.pdf', 50)

def test_with_pdf_885():
    # Justitiedepartementet/2022
    assert_document_parser_size('tmp/885/37864.pdf', 25)

def test_with_pdf_1114():
    # Miljö- och energidepartementet/2015
    assert_document_parser_size('tmp/1114/44311.pdf', 16)

def test_with_pdf_1259():
    # Finansdepartementet/2016
    assert_document_parser_size('tmp/1259/47863.pdf', 32 )

def test_with_pdf_1262():
    # Justitiedepartementet/2016
    assert_document_parser_size('tmp/1262/47866.pdf', 62)

def test_with_pdf_1334():
    # Näringsdepartementet/2016
    assert_document_parser_size('tmp/1334/50171.pdf', 148)

def test_with_pdf_1356():
    # Kulturdepartementet/2016
    assert_document_parser_size('tmp/1356/50961.pdf', 123)

def test_with_pdf_1368():
    # Justitiedepartementet/2016
    assert_document_parser_size('tmp/1368/51107.pdf', 75)

def test_with_pdf_1401():
    # Justitiedepartementet/2016
    assert_document_parser_size('tmp/1401/52269.pdf', 24)

def test_with_pdf_1460():
    # Utbildningsdepartementet/2017
    assert_document_parser_size('tmp/1460/53654.pdf', 89)

def test_with_pdf_1549():
    # Miljö- och energidepartementet/2017
    assert_document_parser_size('tmp/1549/56528.pdf', 128)

def test_with_pdf_1597():
    # Näringsdepartementet/2017
    assert_document_parser_size('tmp/1597/57682.pdf', 103)

def test_with_pdf_1864():
    # Näringsdepartementet/2018
    assert_document_parser_size('tmp/1864/67023.pdf', 159)

def test_with_pdf_1949():
    # Infrastrukturdepartementet/2019
    assert_document_parser_size('tmp/1949/70170.pdf', 27)
