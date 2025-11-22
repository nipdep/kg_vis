from streamlit_agraph import agraph, Node, Edge, Config

from core.query_builder import replace_prefixes_if_uri, is_resource
from core.graph_builder import get_edge_color
from config.settings import FABIO_WORK
from core.work_graph import get_argument_neighbors, _get_first_hop

def build_work_overview_graph(works):
    nodes = []
    edges = []

    for w in works:
        label = w["label"]
        year  = w["year"]
        title = f"{label} ({year})" if year else label

        nodes.append(
            Node(
                id=w["uri"],
                label=label[:40],      # keep graph compact
                title=title,           # full title on hover
                size=15,
                color="#000000",
                shape="dot"
            )
        )

    cfg = Config(
        width="100%",
        height=500,
        directed=True,
        nodes={"font": {"size": 10}},
        edges={"smooth": False},
        interaction={"hover": True}
    )

    clicked = agraph(nodes=nodes, edges=edges, config=cfg)
    return clicked

def build_layered_work_graph(rows, work_uri: str,
                             show_structure: bool,
                             show_argument: bool):
    """
    Build nodes & edges for streamlit_agraph from a local graph.
    Only include layers requested by the user.
    """
    nodes = {}
    edges = []

    def ensure_node(uri, type_iri=None, label=None, is_work=False, layer="other"):
        if uri in nodes:
            return

        # 1) label in graph = type prefix, not literal text
        display_label = "Work" if is_work else replace_prefixes_if_uri(type_iri or uri)

        # 2) hover title = actual label or URI
        hover_title = label or uri

        # 3) color by layer
        if is_work:
            color = "#000000"
        elif layer == "structure":
            color = "#F6E3A1"  # soft yellow
        elif layer == "argument":
            color = "#C7F3C3"  # soft green
        else:
            color = "#CCCCCC"

        nodes[uri] = Node(
            id=uri,
            label=display_label[:30],
            title=hover_title[:300],
            size=18 if is_work else 12,
            color=color,
            shape="box" if is_work else "ellipse"
        )

    # always add the work node itself
    ensure_node(work_uri, type_iri=FABIO_WORK, is_work=True, layer="work")

    for row in rows:
        layer = row.get("layer", {}).get("value", "other")

        # skip rows for layers the user has turned off
        if layer == "structure" and not show_structure:
            continue
        if layer == "argument" and not show_argument:
            continue

        s = row["s"]["value"]
        p = row["p"]["value"]
        o = row["o"]["value"]
        s_type = row.get("sType", {}).get("value")
        o_type = row.get("oType", {}).get("value")
        label = row.get("label", {}).get("value")

        # no literal nodes in the collapsed view
        if not is_resource(o):
            # we still want the edge label as information in the table later,
            # but we don't visualize this literal node.
            ensure_node(s, type_iri=s_type, layer=layer)
            continue

        ensure_node(s, type_iri=s_type, layer=layer)
        ensure_node(o, type_iri=o_type, label=label, layer=layer)

        edges.append(
            Edge(
                source=s,
                target=o,
                label=replace_prefixes_if_uri(p),
                color=get_edge_color(p),
                arrows_to=True,
                type="CURVE_SMOOTH"
            )
        )

    return list(nodes.values()), edges


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