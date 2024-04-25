import sys
from SPARQLWrapper import SPARQLWrapper, JSON

endpoint_url = "https://query.wikidata.org/sparql"

query = """
SELECT DISTINCT ?orgLabel ?typeLabel WHERE {
  BIND(wd:Q34 AS ?country)
  {
    VALUES ?type {
      wd:Q68295960
      wd:Q107407151
      wd:Q127448
      wd:Q1754161
      wd:Q10397683
      wd:Q59603261
      wd:Q10330441
      wd:Q341627
      wd:Q2065704
      wd:Q190752
      wd:Q1289455
      wd:Q18292311
      wd:Q10530889
    }
    ?org wdt:P31 ?type;
      wdt:P17 ?country.
  }
  UNION
  {
    VALUES ?type {
      wd:Q108059166
      wd:Q108058047
      wd:Q3917681
    }
    ?org wdt:P31 ?type;
      wdt:P137 ?country.
  }
  UNION
  {
    VALUES ?org {
      wd:Q10475844
    }
  }
  MINUS { ?org wdt:P576 _:b15. }
  MINUS { ?org wdt:P1366 _:b16. }
  MINUS { ?org wdt:P3999 _:b17. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "sv,en". }
}
ORDER BY (?typeLabel)"""


def get_government_organisations():
    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    # TODO adjust user agent; see https://w.wiki/CX6
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    results = results["results"]["bindings"]
    results = [org['orgLabel']['value'] for org in results]

    return results

