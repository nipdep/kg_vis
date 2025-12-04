from typing import List, Dict 


from core.query_builder import replace_prefixes_if_uri, is_resource
from core.graph_builder import get_edge_color
from config.settings import FABIO_WORK
from core.work_graph import get_argument_neighbors, _get_first_hop
from ui.styling import ARGUMENT_TYPE_COLORS, DEFAULT_ARGUMENT_COLOR
from pyvis.network import Network
import streamlit as st



# -----------------------------
# Helpers
# -----------------------------

def _local_name(uri: str) -> str:
    if "#" in uri:
        return uri.rsplit("#", 1)[1]
    if "/" in uri:
        return uri.rstrip("/").rsplit("/", 1)[1]
    if ":" in uri:
        return uri.rsplit(":", 1)[1]
    return uri


def _pretty_keyword_label(s: str) -> str:
    for prefix in ["idea:", "cso:",
                   "http://www.semanticweb.org/idea/",
                   "http://cso.kmi.open.ac.uk/schema/cso#"]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.replace("_", " ")


def _guess_kind(uri: str, type_iri: str | None, layer: str, work_uri: str) -> str:
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


# ------------------------------------------
#   PyVis Graph – WORK-CENTRIC BUILDER
# ------------------------------------------

def build_layered_work_graph(
    rows: List[Dict],
    work_uri: str,
    show_structure: bool,
    show_argument: bool,
    show_metadata: bool,
):
    """
    Build a clean PyVis graph:
    - groups shown as BIG BUBBLE clusters
    - predicate-based sub-clusters inside
    - colored argument types
    """

    net = Network(
        height="750px",
        width="100%",
        directed=True,
        bgcolor="#FFFFFF",
        font_color="#333333",
    )

    net.barnes_hut(
        gravity=-30000,
        spring_length=140,
        spring_strength=0.002,
        central_gravity=0.15
    )

    # -----------------------------------
    # 1. Collect nodes
    # -----------------------------------
    def add_node(uri, type_iri, label, layer):
        kind = _guess_kind(uri, type_iri, layer, work_uri)

        # choose color
        if kind == "work":
            color = "#FFFFFF"
            shape = "box"
        elif kind == "person":
            color = "#A8C8FF"
            shape = "ellipse"
        elif kind == "keyword":
            color = "#DDDDDD"
            shape = "ellipse"
        elif kind == "event":
            color = "#E6CCFF"
            shape = "ellipse"
        elif kind == "section":
            color = "#FFF6A6"
            shape = "ellipse"
        elif kind == "argument":
            color = "#C7F3C3"
            shape = "box"
        elif kind == "argument_neighbor":
            color = ARGUMENT_TYPE_COLORS.get(type_iri, DEFAULT_ARGUMENT_COLOR)
            shape = "ellipse"
        else:
            color = "#CCCCCC"
            shape = "ellipse"

        # pretty label
        if kind == "keyword":
            display = _pretty_keyword_label(label or _local_name(uri))
        else:
            display = label or _local_name(uri)

        net.add_node(
            uri,
            label=display[:40],
            title=uri,
            color=color,
            shape=shape,
            borderWidth=1,
        )

    # always add work node
    add_node(work_uri, FABIO_WORK, None, "structure")

    node_types = {}
    edges = []

    for r in rows:
        layer = r.get("layer", {}).get("value")

        if layer == "structure" and not show_structure:
            continue
        if layer in ("argument", "argument_neighbor") and not show_argument:
            continue
        if layer == "metadata" and not show_metadata:
            continue

        s = r["s"]["value"]
        p = r["p"]["value"]
        o = r["o"]["value"]

        s_type = r.get("sType", {}).get("value")
        o_type = r.get("oType", {}).get("value")
        o_label = r.get("label", {}).get("value")

        if not is_resource(o):
            add_node(s, s_type, None, layer)
            continue

        if p.endswith("rdf:type") or p.endswith("rdf-syntax-ns#type"):
            continue

        add_node(s, s_type, None, layer)
        add_node(o, o_type, o_label, layer)

        edges.append((s, o, replace_prefixes_if_uri(p)))

    # --------------------------------------
    # 2. BUILD BIG BUBBLE CLUSTERS (PyVis Compatible)
    # --------------------------------------

    # group name → node list
    groups = {
        "people": [],
        "keywords": [],
        "events": [],
        "sections": [],
        "arguments": [],
        "other": [],
    }

    # Step 1: classify nodes into groups
    def group_for(uri):
        t = None
        for r in rows:
            if r["s"]["value"] == uri:
                t = r.get("sType", {}).get("value")
            if r["o"]["value"] == uri:
                t = r.get("oType", {}).get("value")

        k = _guess_kind(uri, t, "other", work_uri)
        return {
            "person": "people",
            "keyword": "keywords",
            "event": "events",
            "section": "sections",
            "argument": "arguments",
            "argument_neighbor": "arguments",
            "work": "other",
        }.get(k, "other")

    # bucket nodes
    for n in net.nodes:
        uri = n["id"]
        grp = group_for(uri)
        groups[grp].append(uri)

    # Step 2 — create virtual "bubble center" nodes
    for grp, uris in groups.items():
        if not uris:
            continue

        cid = f"_cluster_{grp}"
        net.add_node(
            cid,
            label=grp.upper(),
            color="rgba(200,200,200,0.15)",   # transparent grey bubble
            shape="ellipse",
            size=80,
            physics=False,                   # fixed center
            font={"size": 22},
        )

        # Step 3 — connect children to parent bubble using invisible edges
        for u in uris:
            net.add_edge(
                cid,
                u,
                color="rgba(0,0,0,0)",
                width=0.1,
                smooth=False,
                arrows="",         # no arrow
            )

    # --------------------------------------
    # 4. Render inside Streamlit
    # --------------------------------------
    html = net.generate_html("pyvis_graph.html")
    st.components.v1.html(html, height=800, scrolling=True)
