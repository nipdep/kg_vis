from typing import List, Dict 

from streamlit_agraph import agraph, Node, Edge, Config

from core.query_builder import replace_prefixes_if_uri, is_resource
from core.graph_builder import get_edge_color
from config.settings import FABIO_WORK
from core.work_graph import get_argument_neighbors, _get_first_hop

def _local_name(uri: str) -> str:
    """
    Last fragment after #, / or : – good for IDs like idea:tog.
    """
    if "#" in uri:
        return uri.rsplit("#", 1)[1]
    if "/" in uri:
        return uri.rstrip("/").rsplit("/", 1)[1]
    if ":" in uri:
        return uri.rsplit(":", 1)[1]
    return uri


def _pretty_keyword_label(s: str) -> str:
    """
    Remove common KG prefixes and make label human-ish.
    """
    for prefix in ("idea:", "cso:", "http://www.semanticweb.org/idea/", "http://cso.kmi.open.ac.uk/schema/cso#"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    s = s.replace("_", " ")
    return s

def _guess_kind(uri: str, type_iri: str | None, layer: str, work_uri: str) -> str:
    """
    Map a node to a semantic kind so we can style it.
    """
    if uri == work_uri:
        return "work"

    if layer == "argument":
        return "argument"
    if layer == "argument_neighbor":
        return "argument_neighbor"

    t = type_iri or ""

    if t.startswith("http://xmlns.com/foaf/0.1/") or "Person" in t:
        return "person"

    if t.startswith("http://purl.org/spar/deo/"):
        return "section"

    if t.startswith("http://cso.kmi.open.ac.uk/schema/cso#") or "Topic" in t:
        return "keyword"

    if "Conference" in t or "Event" in t or t.startswith("http://purl.org/ontology/bibo/"):
        return "event"

    return "other"

# ---------------------------
# overview graph (all works)
# ---------------------------

def build_work_overview_graph(
    works: List[Dict],
    citations: List[Dict] | None = None
):
    """
    Nodes: all works in gray boxes with paper id.
    Hover: full paper title (and year if available).
    Edges: citation links if provided.
    """
    nodes = []
    edges = []

    works_by_uri = {w["uri"]: w for w in works}

    for w in works:
        uri = w["uri"]
        label = _local_name(uri)
        title = w["label"]
        year = w.get("year")
        if year:
            title = f"{title} ({year})"

        nodes.append(
            Node(
                id=uri,
                label=label[:30],
                title=title,
                size=18,
                color="#DDDDDD",
                shape="box",
                group="work"
            )
        )

    if citations:
        for c in citations:
            src = c["source"]
            tgt = c["target"]
            if src not in works_by_uri or tgt not in works_by_uri:
                continue
            edges.append(
                Edge(
                    source=src,
                    target=tgt,
                    arrows_to=True,
                    color="#BBBBBB",
                    type="STRAIGHT"
                )
            )

    cfg = Config(
        width="100%",
        height=500,
        directed=True,
        interaction={"hover": True},
        nodes={"font": {"size": 10}},
        edges={"smooth": False},
        groups={
            "work": {
                "shape": "box",
            }
        }
    )

    clicked = agraph(nodes=nodes, edges=edges, config=cfg)
    return clicked

# ---------------------------
# detailed per-work graph
# ---------------------------

def build_layered_work_graph(
    rows: List[Dict],
    work_uri: str,
    show_structure: bool,
    show_argument: bool,
    show_metadata: bool,
):
    """
    Build nodes & edges for a single work, respecting toggles.
    - structure layer   -> deo/doco/fabio/etc.
    - argument layer    -> amo/idea/semsur + their neighbors
    - metadata layer    -> authors, venue, keywords
    """
    nodes: dict[str, Node] = {}
    edges: List[Edge] = []

    def ensure_node(
        uri: str,
        type_iri: str | None,
        label: str | None,
        layer: str,
    ):
        if uri in nodes:
            return

        kind = _guess_kind(uri, type_iri, layer, work_uri)

        # --- label & hover title ---
        if kind == "work":
            display_label = _local_name(uri)
            hover_title = label or uri
        elif kind == "keyword":
            base = label or _local_name(uri)
            display_label = _pretty_keyword_label(base)
            hover_title = base
        elif kind == "section":
            # show section type as label
            display_label = replace_prefixes_if_uri(type_iri or uri)
            hover_title = label or uri
        elif kind == "person":
            display_label = label or _local_name(uri)
            hover_title = label or uri
        elif kind in ("argument", "argument_neighbor"):
            display_label = (label or replace_prefixes_if_uri(type_iri or uri))[:30]
            hover_title = label or uri
        else:
            display_label = replace_prefixes_if_uri(type_iri or uri)
            hover_title = label or uri

        # --- color & shape ---
        if kind == "work":
            color = "#FFFFFF"
            shape = "box"
            size = 22
        elif kind == "person":
            color = "#B3D1FF"  # blue-ish
            shape = "ellipse"
            size = 14
        elif kind == "keyword":
            color = "#DDDDDD"
            shape = "ellipse"
            size = 12
        elif kind == "event":
            color = "#E1C8FF"  # purple
            shape = "ellipse"
            size = 14
        elif kind == "section":
            color = "#FFF6B3"  # yellow
            shape = "ellipse"
            size = 14
        elif kind == "argument":
            color = "#C7F3C3"  # green
            shape = "box"
            size = 16
        elif kind == "argument_neighbor":
            color = "#A4E8A0"
            shape = "ellipse"
            size = 12
        else:
            color = "#CCCCCC"
            shape = "ellipse"
            size = 10

        group = {
            "work": "work",
            "person": "people",
            "keyword": "keywords",
            "event": "events",
            "section": "sections",
            "argument": "arguments",
            "argument_neighbor": "arguments",
        }.get(kind, "other")

        nodes[uri] = Node(
            id=uri,
            label=display_label[:30],
            title=hover_title[:300],
            size=size,
            color=color,
            shape=shape,
            group=group,
        )

    # always add work node
    ensure_node(work_uri, type_iri=FABIO_WORK, label=None, layer="structure")

    for row in rows:
        layer = row.get("layer", {}).get("value", "other")

        # respect toggles
        if layer == "structure" and not show_structure:
            continue
        if layer in ("argument", "argument_neighbor") and not show_argument:
            continue
        if layer == "metadata" and not show_metadata:
            continue

        s = row["s"]["value"]
        p = row["p"]["value"]
        o = row["o"]["value"]

        s_type = row.get("sType", {}).get("value")
        o_type = row.get("oType", {}).get("value")

        label = row.get("label", {}).get("value")

        # collapsed view: no literal nodes
        if not is_resource(o):
            ensure_node(s, type_iri=s_type, label=None, layer=layer)
            continue

        ensure_node(s, type_iri=s_type, label=None, layer=layer)
        ensure_node(o, type_iri=o_type, label=label, layer=layer)

        edges.append(
            Edge(
                source=s,
                target=o,
                label=replace_prefixes_if_uri(p),
                color=get_edge_color(p),
                arrows_to=True,
                type="CURVE_SMOOTH",
            )
        )

    cfg = Config(
        width="100%",
        height=700,
        directed=True,
        interaction={"hover": True},
        nodes={"font": {"size": 10}},
        edges={"font": {"size": 8}},
        groups={
            "work": {"shape": "box"},
            "people": {"shape": "ellipse"},
            "keywords": {"shape": "ellipse"},
            "events": {"shape": "ellipse"},
            "sections": {"shape": "ellipse"},
            "arguments": {"shape": "box"},
        },
    )

    clicked = agraph(nodes=list(nodes.values()), edges=edges, config=cfg)
    return clicked

def get_work_local_graph(endpoint: str, work_uri: str, expand_arguments=False):
    """
    1-hop around Work
    + OPTIONAL 2-hop for argumentation graph
    """
    rows = _get_first_hop(endpoint, work_uri)

    if not expand_arguments:
        return rows

    # identify argument nodes
    arg_nodes = []
    for row in rows:
        o = row["o"]["value"]
        t = row.get("oType", {}).get("value")
        if t and (
            t.startswith("http://purl.org/spar/amo/") or
            t.startswith("http://www.semanticweb.org/idea/") or
            t.startswith("http://purl.org/semsur/")
        ):
            arg_nodes.append(o)

    if not arg_nodes:
        return rows

    # 2-hop expansion
    second_hop = get_argument_neighbors(endpoint, arg_nodes)
    return rows + second_hop