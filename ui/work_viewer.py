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
                color="#FFFFFFD3",
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

# def build_layered_work_graph(rows, work_uri: str,
#                              show_structure: bool,
#                              show_argument: bool):

#     nodes = {}
#     edges = []

#     def ensure_node(uri, type_iri=None, label=None, is_work=False, layer="other"):
#         if uri in nodes:
#             return

#         # 1) label in graph = type prefix, not literal text
#         display_label = "Work" if is_work else replace_prefixes_if_uri(type_iri or uri)

#         # 2) hover title = actual label or URI
#         hover_title = label or uri

#         # 3) color by layer
#         if is_work:
#             color = "#000000"
#         elif layer == "structure":
#             color = "#F6E3A1"  # soft yellow
#         elif layer == "argument":
#             color = "#C7F3C3"  # soft green
#         else:
#             color = "#CCCCCC"

#         nodes[uri] = Node(
#             id=uri,
#             label=display_label[:30],
#             title=hover_title[:300],
#             size=18 if is_work else 12,
#             color=color,
#             shape="box" if is_work else "ellipse"
#         )

#     # always add the work node itself
#     ensure_node(work_uri, type_iri=FABIO_WORK, is_work=True, layer="work")

#     for row in rows:
#         layer = row.get("layer", {}).get("value", "other")

#         # skip rows for layers the user has turned off
#         if layer == "structure" and not show_structure:
#             continue
#         if layer == "argument" and not show_argument:
#             continue

#         s = row["s"]["value"]
#         p = row["p"]["value"]
#         o = row["o"]["value"]
#         s_type = row.get("sType", {}).get("value")
#         o_type = row.get("oType", {}).get("value")
#         label = row.get("label", {}).get("value")

#         # no literal nodes in the collapsed view
#         if not is_resource(o):
#             # we still want the edge label as information in the table later,
#             # but we don't visualize this literal node.
#             ensure_node(s, type_iri=s_type, layer=layer)
#             continue

#         ensure_node(s, type_iri=s_type, layer=layer)
#         ensure_node(o, type_iri=o_type, label=label, layer=layer)

#         edges.append(
#             Edge(
#                 source=s,
#                 target=o,
#                 label=replace_prefixes_if_uri(p),
#                 color=get_edge_color(p),
#                 arrows_to=True,
#                 type="CURVE_SMOOTH"
#             )
#         )

#     # render
#     cfg = Config(
#         width="100%",
#         height=700,
#         directed=True,
#         interaction={"hover": True},
#         nodes={"font": {"size": 10}},
#         edges={"font": {"size": 8}},
#     )

#     clicked = agraph(nodes=list(nodes.values()), edges=edges, config=cfg)   
#     return clicked

def build_layered_work_graph(
    rows,
    work_uri: str,
    show_structure: bool,
    show_argument: bool,
):
    """
    Build and render the Work-centric graph according to the spec:

    Entity types & styles (default view):

    - work                 | square | white   | paper id
    - person               | ellipse| blue    | name
    - keyword              | ellipse| gray    | keyword label
    - event                | ellipse| purple  | event_id
    - section              | ellipse| yellow  | section type
    - argument             | square | green   | title
    - arg neighbors (≠work)| ellipse| green   | node type

    Hover and click behaviour:
      - We only handle label/hover here. Click behaviour is handled by app.py
        (details table of all one-hop triples for selected node).
    """

    # -------------------------------------------------------
    # PREPASS: collect labels, types, argument cores & neighbors,
    #          section element counts, event years
    # -------------------------------------------------------
    node_types = {}   # uri -> primary rdf:type
    node_labels = {}  # uri -> human-readable label
    arg_core_nodes = set()
    arg_neighbor_nodes = set()
    section_child_counts = {}
    event_years = {}

    def _set_type(uri, t):
        if not t:
            return
        if uri not in node_types:
            node_types[uri] = t

    def _set_label(uri, label):
        if not label:
            return
        if uri not in node_labels:
            node_labels[uri] = label

    def _is_argument_type(t: str) -> bool:
        if not t:
            return False
        return (
            t.startswith("http://purl.org/spar/amo/")
            or t.startswith("http://www.semanticweb.org/idea/")
            or t.startswith("http://purl.org/semsur/")
        )

    def _is_section_type(t: str) -> bool:
        if not t:
            return False
        return (
            t.startswith("http://purl.org/spar/doco/")
            or t.startswith("http://purl.org/spar/deo/")
        )

    def _is_event_type(t: str) -> bool:
        if not t:
            return False
        # heuristic, adapt if you know exact event classes
        return (
            "Conference" in t
            or "Event" in t
            or t.startswith("http://purl.org/semsur/")
        )

    def _is_person_type(t: str) -> bool:
        if not t:
            return False
        return (
            "foaf/Person" in t
            or t.endswith("Person")
            or "schema.org/Person" in t
        )

    def _is_keyword_type(t: str) -> bool:
        if not t:
            return False
        return (
            t.startswith("http://cso.kmi.open.ac.uk/schema/cso#")
            or t.startswith("http://www.w3.org/2004/02/skos/core#")
        )
    
    def _local_name(uri: str) -> str:
        if not uri:
            return uri
        if "#" in uri:
            return uri.rsplit("#", 1)[-1]
        return uri.rstrip("/").rsplit("/", 1)[-1]

    # First pass: types & labels
    for row in rows:
        s = row["s"]["value"]
        o = row["o"]["value"]
        s_type = row.get("sType", {}).get("value")
        o_type = row.get("oType", {}).get("value")
        label = row.get("label", {}).get("value")

        _set_type(s, s_type)
        _set_type(o, o_type)
        # label is always for "o" in your query
        if is_resource(o):
            _set_label(o, label)

    # Argument core nodes: any node whose type is amo:/idea:/semsur:
    for uri, t in node_types.items():
        if _is_argument_type(t):
            arg_core_nodes.add(uri)

    # Second pass: identify argument neighbors & section element counts, event years
    for row in rows:
        s = row["s"]["value"]
        o = row["o"]["value"]
        p = row["p"]["value"]
        layer = row.get("layer", {}).get("value", "other")

        s_type = node_types.get(s)
        o_type = node_types.get(o)

        # neighbors-of-argument (excluding the Work)
        if layer == "argument":
            if s in arg_core_nodes and o not in arg_core_nodes and o != work_uri:
                arg_neighbor_nodes.add(o)
            if o in arg_core_nodes and s not in arg_core_nodes and s != work_uri:
                arg_neighbor_nodes.add(s)

        # section element counts: number of structural edges from section nodes
        if layer == "structure" and _is_section_type(s_type):
            section_child_counts[s] = section_child_counts.get(s, 0) + 1

        # event year: look for literal year-ish properties
        if _is_event_type(s_type) and not is_resource(o):
            if "date" in p or "year" in p or "issued" in p:
                event_years[s] = o

    # -------------------------------------------------------
    # NODE CREATION
    # -------------------------------------------------------
    nodes = {}
    edges = []

    def classify_category(uri: str, type_iri: str | None) -> str:
        """
        Return one of:
          'work', 'argument', 'argument-neighbor',
          'person', 'keyword', 'event', 'section', 'other'
        """
        if uri == work_uri:
            return "work"
        if uri in arg_core_nodes:
            return "argument"
        if uri in arg_neighbor_nodes:
            return "argument-neighbor"

        if _is_person_type(type_iri):
            return "person"
        if _is_keyword_type(type_iri):
            return "keyword"
        if _is_event_type(type_iri):
            return "event"
        if _is_section_type(type_iri):
            return "section"

        return "other"

    def ensure_node(uri, layer="other"):
        if uri in nodes:
            return

        type_iri = node_types.get(uri)
        label = node_labels.get(uri)
        category = classify_category(uri, type_iri)

        # default label & hover
        node_label = replace_prefixes_if_uri(type_iri or uri)
        hover = label or uri

        shape = "ellipse"
        color = "#CCCCCC"  # default gray
        size = 12

        # --- apply per-entity styling rules ---
        if category == "work":
            shape = "box"
            color = "#FFFFFF"
            size = 22
            node_label = _local_name(uri)  # paper id

            # hover: paper title + venue id (best-effort)
            title = label or uri
            hover_parts = [title]

            # best-effort venue: first event node attached to the work
            venue_id = None
            for r in rows:
                if r["s"]["value"] == work_uri:
                    o_uri = r["o"]["value"]
                    if o_uri != work_uri and _is_event_type(node_types.get(o_uri)):
                        venue_id = _local_name(o_uri)
                        break
            if venue_id:
                hover_parts.append(venue_id)

            hover = "\n".join(hover_parts)

        elif category == "person":
            shape = "ellipse"
            color = "#4C6FFF"  # blue
            size = 14
            node_label = label or _local_name(uri)
            hover = ""  # "nothing" on hover

        elif category == "keyword":
            shape = "ellipse"
            color = "#888888"  # gray
            size = 12
            node_label = label or _local_name(uri)
            hover = ""

        elif category == "event":
            shape = "ellipse"
            color = "#A259FF"  # purple
            size = 14
            node_label = _local_name(uri)  # event_id

            # hover: event name + year
            name = label or ""
            year = event_years.get(uri, "")
            hover = "\n".join([x for x in [name, year] if x]).strip()

        elif category == "section":
            shape = "ellipse"
            color = "#FFD966"  # yellow
            size = 14
            node_label = replace_prefixes_if_uri(type_iri or "Section")

            count = section_child_counts.get(uri, 0)
            hover = f"{count} elements" if count else ""

        elif category == "argument":
            shape = "box"
            color = "#5CB85C"  # green
            size = 16
            node_label = label or _local_name(uri)
            hover = ""

        elif category == "argument-neighbor":
            shape = "ellipse"
            color = "#5CB85C"  # green
            size = 12
            node_label = replace_prefixes_if_uri(type_iri or uri)
            hover = label or ""

        # category == "other" keeps defaults

        nodes[uri] = Node(
            id=uri,
            label=node_label[:40],
            title=hover[:300],
            size=size,
            color=color,
            shape=shape,
        )

    # always add the central work node
    ensure_node(work_uri, layer="work")

    # -------------------------------------------------------
    # EDGES + NODES FROM TRIPLES
    # -------------------------------------------------------
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

        # collapsed view: no literal nodes
        if not is_resource(o):
            ensure_node(s, layer=layer)
            continue

        ensure_node(s, layer=layer)
        ensure_node(o, layer=layer)

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

    # -------------------------------------------------------
    # RENDER + RETURN CLICKED NODE
    # -------------------------------------------------------
    cfg = Config(
        width="100%",
        height=700,
        directed=True,
        interaction={"hover": True},
        nodes={"font": {"size": 10}},
        edges={"font": {"size": 8}},
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