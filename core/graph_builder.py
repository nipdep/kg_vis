from streamlit_agraph import Node, Edge

from core.query_builder import replace_prefixes_if_uri

def get_edge_color(p: str):
    return "#666666"

def triples_to_graph(triples):
    nodes = {}
    edges = []

    for row in triples:
        s = row["s"]["value"]
        p = row["p"]["value"]
        o = row["o"]["value"]

        if s not in nodes:
            nodes[s] = Node(id=s, label=s, size=12, color="#333333")

        if o not in nodes:
            nodes[o] = Node(id=o, label=o, size=12, color="#999999")

        edges.append(
            Edge(
                source=s,
                target=o,
                label=replace_prefixes_if_uri(p),
                arrows_to=True
            )
        )

    return list(nodes.values()), edges

def get_edge_color(p: str):
    if p.startswith("http://purl.org/spar/amo/"):
        return "#D9376E"   # argument edges: red-ish
    if p.startswith("http://www.semanticweb.org/idea/"):
        return "#FF8C42"   # idea edges: orange
    if p.startswith("http://purl.org/semsur/"):
        return "#FF5F00"   # semsur edges: orange
    if p.startswith("http://purl.org/spar/doco/") or \
       p.startswith("http://purl.org/spar/deo/"):
        return "#4CB5AE"   # document structure: teal
    if p.startswith("http://purl.org/spar/fabio/"):
        return "#4A8FE7"   # fabio relations: blue
    if p.startswith("http://xmlns.com/foaf/"):
        return "#9B6CC1"   # foaf: purple
    if p.startswith("http://www.w3.org/2000/01/rdf-schema#"):
        return "#666666"
    return "#999999"       # fallback
