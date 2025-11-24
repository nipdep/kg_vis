from typing import List, Dict

from core.sparql_client import sparql
from core.query_builder import build_query

from config.settings import ARGUMENT_PREFIXES, STRUCTURE_PREFIXES, PERSON_PREFIXES, KEYWORD_PREFIXES, EVENT_PREFIXES, CITATION_PROPS, CITO_NS, FABIO_NS
from core.graph_builder import triples_to_graph

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

def _iri_or_tests(var: str, prefixes: List[str]) -> str:
    if not prefixes:
        return "false"
    return " || ".join([f'STRSTARTS(STR({var}), "{p}")' for p in prefixes])


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

def get_citation_edges(sparql_endpoint: str, limit: int = 2000):
    """
    Return directed citation edges between Works.
    An edge exists if ?citing ?p ?cited and ?p rdfs:subPropertyOf* cito:cites.
    Both endpoints must be fabio:Work (or subclass) instances.
    """
    query = build_query(f"""
    SELECT DISTINCT ?citing ?cited ?p
    WHERE {{
        ?citing rdf:type ?t1 .
        ?t1 rdfs:subClassOf* fabio:Work .

        ?cited  rdf:type ?t2 .
        ?t2 rdfs:subClassOf* fabio:Work .

        ?citing ?p ?cited .
        ?p rdfs:subPropertyOf* cito:cites .
    }}
    LIMIT {limit}
    """)

    rows = sparql(sparql_endpoint, query)

    edges = []
    for r in rows:
        edges.append({
            "source": r["citing"]["value"],
            "target": r["cited"]["value"],
            "predicate": r["p"]["value"],
        })
    return edges

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

# ---------------------------
# all works + basic metadata
# ---------------------------

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

# ---------------------------
# citations across works
# ---------------------------

def get_work_citations(sparql_endpoint: str) -> List[Dict[str, str]]:
    """
    Return citation edges between work nodes.
    """
    prop_filters = " || ".join([f"(?p = <{p}>)" for p in CITATION_PROPS]) or "false"

    q = build_query(f"""
    SELECT DISTINCT ?citing ?cited
    WHERE {{
        ?citing rdf:type ?t1 .
        ?t1 rdfs:subClassOf* fabio:Work .

        ?cited rdf:type ?t2 .
        ?t2 rdfs:subClassOf* fabio:Work .

        ?citing ?p ?cited .
        FILTER({prop_filters})
    }}
    """)

    rows = sparql(sparql_endpoint, q)
    edges = []
    for r in rows:
        edges.append({
            "source": r["citing"]["value"],
            "target": r["cited"]["value"]
        })
    return edges

# ---------------------------
# sidebar – keyword cloud
# ---------------------------

def get_top_keywords(sparql_endpoint: str, limit: int = 30):
    """
    Top discipline keywords (fabio:hasDiscipline) across works.
    """
    q = build_query(f"""
    SELECT ?kw (COUNT(*) AS ?count)
    WHERE {{
        ?work rdf:type ?type .
        ?type rdfs:subClassOf* fabio:Work .

        ?work fabio:hasDiscipline ?kw .
    }}
    GROUP BY ?kw
    ORDER BY DESC(?count)
    LIMIT {limit}
    """)

    rows = sparql(sparql_endpoint, q)
    return [
        {"uri": r["kw"]["value"], "count": int(r["count"]["value"])}
        for r in rows
    ]

# ---------------------------
# section hierarchy
# ---------------------------

def get_section_hierarchy(sparql_endpoint: str, work_uri: str):
    """
    For now: one-level hierarchy – work -> sections.
    Uses po:contains and deo:* section types.
    """
    q = build_query(f"""
    SELECT DISTINCT ?sec ?secType ?secTypeLabel
    WHERE {{
        <{work_uri}> po:contains ?sec .

        OPTIONAL {{ ?sec rdf:type ?secType . }}
        OPTIONAL {{ ?secType rdfs:label ?secTypeLabel }}
    }}
    ORDER BY ?sec
    """)

    rows = sparql(sparql_endpoint, q)
    sections = []
    for r in rows:
        sec = r["sec"]["value"]
        t = r.get("secType", {}).get("value")
        label = r.get("secTypeLabel", {}).get("value")
        sections.append({"uri": sec, "type": t, "type_label": label})
    return sections

# ---------------------------
# local graph around a work
# ---------------------------

def _get_first_hop(sparql_endpoint: str, work_uri: str):
    """
    1-hop around work, classify each triple into
    structure / argument / metadata / other.
    """
    struct_tests = _iri_or_tests("?type", STRUCTURE_PREFIXES)
    arg_tests = _iri_or_tests("?type", ARGUMENT_PREFIXES)

    person_tests = _iri_or_tests("?type", PERSON_PREFIXES)
    keyword_tests = _iri_or_tests("?type", KEYWORD_PREFIXES)
    event_tests = _iri_or_tests("?type", EVENT_PREFIXES)

    # metadata: people, events, keywords
    meta_tests = f"({person_tests}) || ({keyword_tests}) || ({event_tests})"

    q = build_query(f"""
    SELECT ?s ?p ?o ?sType ?oType ?label ?layer
    WHERE {{
        VALUES ?work {{ <{work_uri}> }}

        {{
            BIND(?work AS ?s)
            ?work ?p ?o .
        }}
        UNION
        {{
            ?s ?p ?work .
            BIND(?work AS ?o)
        }}

        OPTIONAL {{ ?s rdf:type ?sType }}
        OPTIONAL {{ ?o rdf:type ?oType }}

        OPTIONAL {{
            ?o dc:title|dct:title|rdfs:label|skos:prefLabel|
                foaf:name|idea:hasLabel ?label .
        }}

        BIND(COALESCE(?oType, ?sType) AS ?type)

        BIND(
            IF( {arg_tests}, "argument",
                IF( {struct_tests}, "structure",
                    IF( {meta_tests}, "metadata", "other")
                )
            ) AS ?layer
        )
    }}
    """)

    return sparql(sparql_endpoint, q)

def get_argument_neighbors(
    sparql_endpoint: str,
    arg_nodes: List[str]
):
    """
    1-hop neighbors around a set of argument nodes.
    Marked as layer = 'argument_neighbor'.
    """
    if not arg_nodes:
        return []

    values = " ".join(f"<{a}>" for a in arg_nodes)

    q = build_query(f"""
    SELECT ?s ?p ?o ?sType ?oType ?label ?layer
    WHERE {{
        VALUES ?arg {{ {values} }}

        {{
            BIND(?arg AS ?s)
            ?arg ?p ?o .
        }}
        UNION
        {{
            ?s ?p ?arg .
            BIND(?arg AS ?o)
        }}

        FILTER(?s != ?arg || ?o != ?arg)

        OPTIONAL {{ ?s rdf:type ?sType }}
        OPTIONAL {{ ?o rdf:type ?oType }}

        OPTIONAL {{
            ?o dc:title|dct:title|rdfs:label|skos:prefLabel|
                foaf:name|idea:hasLabel ?label .
        }}

        BIND("argument_neighbor" AS ?layer)
    }}
    """)

    return sparql(sparql_endpoint, q)


def get_work_local_graph(
    sparql_endpoint: str,
    work_uri: str,
    expand_arguments: bool = True
):
    """
    Get triples around a given work and classify them as
    'structure' / 'argument' / 'metadata' / 'other'
    plus optional second-hop 'argument_neighbor' nodes.
    """
    rows = _get_first_hop(sparql_endpoint, work_uri)

    if not expand_arguments:
        return rows

    # collect argument nodes
    arg_nodes = set()
    for r in rows:
        layer = r.get("layer", {}).get("value", "")
        if layer != "argument":
            continue
        o = r["o"]["value"]
        arg_nodes.add(o)

    if not arg_nodes:
        return rows

    second_hop = get_argument_neighbors(sparql_endpoint, list(arg_nodes))

    # simple dedup: (s,p,o) triple
    seen = set()
    merged = []
    for r in rows + second_hop:
        key = (r["s"]["value"], r["p"]["value"], r["o"]["value"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(r)

    return merged