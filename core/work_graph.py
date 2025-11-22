
from core.sparql_client import sparql
from core.query_builder import build_query

from config.settings import FABIO_NS, RDF_TYPE, STRUCTURE_PREFIXES, ARGUMENT_PREFIXES
from core.sparql_client import execute_query_convert
from core.graph_builder import triples_to_graph

def get_work_core_triples(endpoint, work):
    query = build_query(f"""
    SELECT ?s ?p ?o WHERE {{
      BIND(<{work}> AS ?s)
      ?s ?p ?o .
      FILTER(?p IN (
         dc:title,
         prism:doi,
         dc:abstract,
         fabio:hasPublicationYear
      ))
    }}
    """)
    return sparql(endpoint, query)

def get_work_structural_triples(endpoint, work):
    query = build_query(f"""
    SELECT ?s ?p ?o WHERE {{
       <{work}> ?p ?o .
       FILTER (
         STRSTARTS(STR(?p), STR(doco:)) ||
         STRSTARTS(STR(?p), STR(deo:))  ||
         STRSTARTS(STR(?p), STR(c4o:))  ||
         STRSTARTS(STR(?p), STR(fabio:)) ||
         STRSTARTS(STR(?p), STR(cso:))   ||
         STRSTARTS(STR(?p), STR(bibo:))  ||
         STRSTARTS(STR(?p), STR(dc:))    ||
         STRSTARTS(STR(?p), STR(foaf:))
       )
    }}
    """)
    return sparql(endpoint, query)

def get_work_argument_triples(endpoint, work):
    query = build_query(f"""
    SELECT ?s ?p ?o WHERE {{
      <{work}> ?p ?o .
      FILTER (
         STRSTARTS(STR(?o), STR(amo:)) ||
         STRSTARTS(STR(?o), STR(idea:)) ||
         STRSTARTS(STR(?o), STR(semsur:))
      )
    }}
    """)
    return sparql(endpoint, query)


def build_work_graph(
    work_uri,
    structural_on: bool,
    argument_on: bool,
    endpoint
):
    """Return graph nodes/edges for the selected Work instance."""

    triples = []

    # Always include the Work node
    triples += get_work_core_triples(endpoint, work_uri)

    # Structural View (fabio, doco, deo, etc.)
    if structural_on:
        structural = get_work_structural_triples(endpoint, work_uri)
        triples += structural

    # Argument View (amo, idea, semsur)
    if argument_on:
        argument = get_work_argument_triples(endpoint, work_uri)
        triples += argument

    # Clean duplicates & convert into nodes/edges
    nodes, edges = triples_to_graph(triples)

    return nodes, edges


def get_all_works(sparql_endpoint: str, limit: int = 500):
    """
    Return all instances of fabio:Work or its subclasses.
    Requires that your ontology (with rdfs:subClassOf links) is loaded
    into the same dataset or exposed via reasoning.
    """
    query = build_query(f"""
    SELECT DISTINCT ?work (SAMPLE(?label0) AS ?label) (SAMPLE(?yearClean) AS ?year)
    WHERE {{
        ?work rdf:type ?type .
        ?type rdfs:subClassOf* fabio:Work .

        OPTIONAL {{ ?work dc:title|dct:title|rdfs:label ?label0 }}

        OPTIONAL {{
            ?work dc:publisher ?event .
            ?event dc:date ?year0 .

            # Keep only the lexical year component and cast to an xsd:gYear
            BIND( xsd:gYear( SUBSTR(STR(?year0), 1, 4) ) AS ?yearClean )
        }}
    }}
    GROUP BY ?work
    ORDER BY LCASE(COALESCE(STR(?label), STR(?work)))
    LIMIT {limit}
    """)

    rows = sparql(sparql_endpoint, query)
    print(f"Fetched {len(rows)} works from endpoint.")
    works = []
    for row in rows:
        uri   = row["work"]["value"]
        label = row.get("label", {}).get("value", uri)
        year  = row.get("year", {}).get("value")
        works.append({"uri": uri, "label": label, "year": year})
    return works


def get_work_local_graph(sparql_endpoint: str, work_uri: str):
    """
    Get triples around a given work and classify them as 'structure' / 'argument' / 'other'.
    """
    struct_iri_tests = " || ".join(
        [f"STRSTARTS(STR(?type), \"{p}\")" for p in STRUCTURE_PREFIXES]
    )
    arg_iri_tests = " || ".join(
        [f"STRSTARTS(STR(?type), \"{p}\")" for p in ARGUMENT_PREFIXES]
    )

    query = f"""
    PREFIX rdf:  <{RDF_TYPE}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dc:   <http://purl.org/dc/elements/1.1/>
    PREFIX dct:  <http://purl.org/dc/terms/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?s ?p ?o ?sType ?oType ?label ?layer
    WHERE {{
        VALUES ?work {{ <{work_uri}> }}

        # edges where work is subject
        {{
            BIND(?work AS ?s)
            ?work ?p ?o .
        }}
        UNION
        # edges where work is object
        {{
            ?s ?p ?work .
            BIND(?work AS ?o)
        }}

        OPTIONAL {{ ?s rdf:type ?sType }}
        OPTIONAL {{ ?o rdf:type ?oType }}

        # human-friendly label / title (for hover & details)
        OPTIONAL {{
            ?o dc:title|dct:title|rdfs:label|skos:prefLabel|foaf:name|<http://www.semanticweb.org/idea/hasLabel> ?label .
        }}

        BIND(COALESCE(?oType, ?sType) AS ?type)

        BIND(
            IF( {arg_iri_tests}, "argument",
                IF( {struct_iri_tests}, "structure", "other")
            ) AS ?layer
        )
    }}
    """

    return execute_query_convert(sparql_endpoint, query)

def get_argument_neighbors(endpoint, nodes):
    """
    Given a list of argument nodes (Claim, Evidence, Warrant, etc.),
    return outgoing and incoming argument triples.
    """
    if not nodes:
        return []

    values = " ".join(f"<{n}>" for n in nodes)

    query = f"""
    PREFIX amo:  <http://purl.org/spar/amo/>
    PREFIX idea: <http://www.semanticweb.org/idea/>
    PREFIX semsur: <http://purl.org/semsur/>

    SELECT ?s ?p ?o ?sType ?oType
    WHERE {{
      VALUES ?center {{ {values} }}

      # out edges
      {{
        ?center ?p ?o .
      }}
      UNION
      # in edges
      {{
        ?s ?p ?center .
      }}

      OPTIONAL {{ ?s rdf:type ?sType }}
      OPTIONAL {{ ?o rdf:type ?oType }}

      FILTER(
           STRSTARTS(STR(?sType), "http://purl.org/spar/amo/")
        || STRSTARTS(STR(?sType), "http://www.semanticweb.org/idea/")
        || STRSTARTS(STR(?sType), "http://purl.org/semsur/")
        || STRSTARTS(STR(?oType), "http://purl.org/spar/amo/")
        || STRSTARTS(STR(?oType), "http://www.semanticweb.org/idea/")
        || STRSTARTS(STR(?oType), "http://purl.org/semsur/")
      )
    }}
    """

    return execute_query_convert(endpoint, query)



def _get_first_hop(endpoint: str, work_uri: str):
    """
    Fetch the direct 1-hop neighborhood around the Work node:
    - All triples where <work> ?p ?o
    - All triples where ?s ?p <work>
    Includes optional types and labels for node classification.
    """

    query = f"""
    PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dc:   <http://purl.org/dc/elements/1.1/>
    PREFIX dct:  <http://purl.org/dc/terms/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

    SELECT ?s ?p ?o ?sType ?oType ?label
    WHERE {{
        VALUES ?work {{ <{work_uri}> }}

        # Outgoing from Work
        {{
            BIND(?work AS ?s)
            ?work ?p ?o .
        }}
        UNION
        # Incoming to Work
        {{
            ?s ?p ?work .
            BIND(?work AS ?o)
        }}

        OPTIONAL {{ ?s rdf:type ?sType }}
        OPTIONAL {{ ?o rdf:type ?oType }}

        # Prefer human labels (for hover/info panel)
        OPTIONAL {{
            ?o dc:title|dct:title|rdfs:label|skos:prefLabel|foaf:name ?label .
        }}
    }}
    """

    return execute_query_convert(endpoint, query)