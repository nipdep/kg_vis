from core.query_builder import build_query
from core.sparql_client import sparql

def search_paper_by_title(endpoint, title):
    query = build_query(f"""
    SELECT ?paper ?label WHERE {{
        ?paper a idea:Paper ;
               rdfs:label ?label .
        FILTER(CONTAINS(LCASE(?label), LCASE("{title}")))
    }}
    LIMIT 100
    """)
    return sparql(endpoint, query)


def get_venues(endpoint):
    query = build_query("""
    SELECT DISTINCT ?venue WHERE {
        ?p a idea:Paper ; idea:hasVenue ?venue .
    }
    """)
    return sparql(endpoint, query)


def get_years(endpoint):
    query = build_query("""
    SELECT DISTINCT ?year WHERE {
        ?p a idea:Paper ; idea:year ?year .
    }
    ORDER BY DESC(?year)
    """)
    return sparql(endpoint, query)


def get_resource_properties(endpoint, resource_uri):
    query = build_query(f"""
    SELECT ?p ?o WHERE {{
        <{resource_uri}> ?p ?o .
    }}
    """)
    return sparql(endpoint, query)

