
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

def _make_prefix_tests(var_name: str, prefixes: list[str]) -> str:
    """Return OR-ed SPARQL STRSTARTS tests for a variable, e.g. ?type."""
    if not prefixes:
        return "false"
    return " || ".join(
        [f"STRSTARTS(STR({var_name}), \"{p}\")" for p in prefixes]
    )


def _is_argument_type_iri(type_iri: str | None) -> bool:
    if not type_iri:
        return False
    return any(
        type_iri.startswith(p)
        for p in ARGUMENT_PREFIXES
    )

def get_work_local_graph(sparql_endpoint: str, work_uri: str):
    """
    Get triples around a given work and classify them as 'structure' / 'argument' / 'other'.

    Steps:
      1. Get all triples where the Work is subject or object (1 hop).
      2. From those, identify all nodes typed in argument namespaces (amo/idea/semsur).
      3. For each such argument node, get its own 1-hop neighbors.
      4. Mark those neighbor triples with layer = "argument".
    """
    struct_iri_tests = _make_prefix_tests("?type", STRUCTURE_PREFIXES)
    arg_iri_tests = _make_prefix_tests("?type", ARGUMENT_PREFIXES)

    # ----------------------------------
    # 1) First hop around the Work node
    # ----------------------------------
    first_query = build_query(f"""
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
            ?o dc:title|dct:title|rdfs:label|skos:prefLabel|foaf:name|idea:hasLabel ?label .
        }}

        BIND(COALESCE(?oType, ?sType) AS ?type)

        BIND(
            IF( {arg_iri_tests}, "argument",
                IF( {struct_iri_tests}, "structure", "other")
            ) AS ?layer
        )
    }}
    """)
    rows = sparql(sparql_endpoint, first_query)

    # ----------------------------------
    # 2) Collect argument nodes from first hop
    # ----------------------------------
    arg_nodes = set()
    for r in rows:
        s = r["s"]["value"]
        o = r["o"]["value"]
        s_type = r.get("sType", {}).get("value")
        o_type = r.get("oType", {}).get("value")

        if _is_argument_type_iri(s_type) and s != work_uri:
            arg_nodes.add(s)
        if _is_argument_type_iri(o_type) and o != work_uri:
            arg_nodes.add(o)

    if not arg_nodes:
        # no argument nodes, nothing extra to add
        return rows
    
    # ----------------------------------
    # 3) Get 1-hop neighbors of all argument nodes in a single query
    # ----------------------------------
    arg_values = " ".join(f"<{u}>" for u in arg_nodes)

    arg_neighbor_query = build_query(
        f"""
    SELECT ?s ?p ?o ?sType ?oType ?label ?layer
    WHERE {{
        VALUES ?arg {{ {arg_values} }}

        {{
            BIND(?arg AS ?s)
            ?arg ?p ?o .
        }}
        UNION
        {{
            ?s ?p ?arg .
            BIND(?arg AS ?o)
        }}

        OPTIONAL {{ ?s rdf:type ?sType }}
        OPTIONAL {{ ?o rdf:type ?oType }}

        OPTIONAL {{
            ?o dc:title|dct:title|rdfs:label|skos:prefLabel|foaf:name|
                idea:hasLabel ?label .
        }}

        # everything here belongs to the argument layer
        BIND("argument" AS ?layer)
    }}
    """
    )

    neighbor_rows = sparql(sparql_endpoint, arg_neighbor_query)

    # ----------------------------------
    # 4) Merge & deduplicate by (s,p,o)
    # ----------------------------------
    all_rows = rows + neighbor_rows
    seen = set()
    unique_rows = [] 

    for r in all_rows:
        s = r["s"]["value"]
        p = r["p"]["value"]
        o = r["o"]["value"]
        key = (s, p, o)
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(r)

    return unique_rows
    # return sparql(sparql_endpoint, query) #execute_query_convert(sparql_endpoint, query)

def get_argument_neighbors(endpoint, nodes):
    """
    Given a list of argument nodes (Claim, Evidence, Warrant, etc.),
    return outgoing and incoming argument triples.
    """
    if not nodes:
        return []

    values = " ".join(f"<{n}>" for n in nodes)

    query = build_query(f"""
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
    """)

    return sparql(endpoint, query) #execute_query_convert(endpoint, query)



def _get_first_hop(endpoint: str, work_uri: str):
    """
    Fetch the direct 1-hop neighborhood around the Work node:
    - All triples where <work> ?p ?o
    - All triples where ?s ?p <work>
    Includes optional types and labels for node classification.
    """

    query = build_query(f"""
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
    """)

    return sparql(endpoint, query) #execute_query_convert(endpoint, query)