from typing import List, Dict 

from streamlit_agraph import agraph, Node, Edge, Config

from core.query_builder import replace_prefixes_if_uri, is_resource
from core.graph_builder import get_edge_color
from config.settings import FABIO_WORK

from core.work_graph import get_argument_neighbors, _get_first_hop
from ui.styling import ARGUMENT_TYPE_COLORS, DEFAULT_ARGUMENT_COLOR, CLASS_STYLE
from ui.ontology_structure import ONTOLOGY_GRAPH

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

# def build_work_overview_graph(works, citations):
#     """
#     Overview graph:
#       - nodes: all works (gray boxes)
#       - edges: explicit cito:cites relations (directed)
#     """
#     nodes = []
#     edges = []

#     work_uris = {w["uri"] for w in works}

#     # -------------------------
#     # Nodes (gray boxes)
#     # -------------------------
#     for w in works:
#         uri = w["uri"]
#         title = w["label"]
#         year = w["year"]

#         hover = f"{title} ({year})" if year else title
#         paper_id = _local_name(uri)

#         nodes.append(
#             Node(
#                 id=uri,
#                 label=paper_id[:30],
#                 title=hover[:300],
#                 size=18,
#                 color="#DDDDDD",
#                 shape="box",
#             )
#         )

#     # -------------------------
#     # Edges: explicit cito:cites only
#     # -------------------------
#     for c in citations:
#         s = c["source"]
#         t = c["target"]

#         # both must be in current filtered set
#         if s not in work_uris or t not in work_uris:
#             continue
        
#         edges.append(
#             Edge(
#                 source=s,
#                 target=t,
#                 label="cites",
#                 color=get_edge_color("cito:cites"),
#                 arrows_to=True,
#                 type="STRAIGHT",
#                 smooth=False,
#             )
#         )

#     cfg = Config(
#         width="100%",
#         height=500,
#         directed=True,
#         interaction={"hover": True},
#         nodes={"font": {"size": 10}},
#         edges={"smooth": False},
#     )

#     clicked = agraph(nodes=nodes, edges=edges, config=cfg)
#     return clicked

def _make_class_node(class_iri: str):
    label = class_iri.split(":")[1]
    color, shape = CLASS_STYLE.get(class_iri, ("#CCCCCC", "ellipse"))

    return Node(
        id=f"class:{class_iri}",
        label=label,
        shape=shape,
        color=color,
        size=28,
        title=f"Class: {class_iri}",
    )

def iri_matches_class(t: str, cls: str) -> bool:
    if not t or ":" not in cls:
        return False
    prefix, name = cls.split(":", 1)
    return t.endswith("/" + name) or t.endswith("#" + name) or t.endswith(name)

def to_curie(iri: str) -> str:
    if "#" in iri:
        iri = iri.split("#", 1)[1]
    if "/" in iri:
        iri = iri.rsplit("/", 1)[1]

    # If it already contains ':', return as-is
    if ":" in iri:
        return iri

    return iri 

def _make_instance_node(uri: str, label: str, class_iri: str):
    base_color, shape = CLASS_STYLE.get(class_iri, ("#CCCCCC", "ellipse"))

    # override for argument types if necessary
    if class_iri.startswith("amo:") or class_iri.startswith("idea:"):
        base_color = ARGUMENT_TYPE_COLORS.get(class_iri, base_color)

    return Node(
        id=uri,
        label=label[:30],
        title=label,
        color=base_color,
        shape=shape,
        size=14,
    )

def build_work_overview_graph(works, citations=None):
    """
    Overview graph:
      - nodes: all works (gray boxes)
      - edges: citation relations (directed citing → cited)
    'citations' is a list of dicts with keys: source, target, predicate
    """
    nodes = []
    edges = []

    work_uris = {w["uri"] for w in works}

    # --- nodes (gray boxes, label = paper id, hover = title) ------------------
    for w in works:
        uri = w["uri"]
        label = w["label"]
        year  = w["year"]

        hover = f"{label} ({year})" if year else label
        paper_id = _local_name(uri)

        nodes.append(
            Node(
                id=uri,
                label=paper_id[:30],
                title=hover[:300],      # full title on hover
                size=18,
                color="#DDDDDD",
                shape="box",
            )
        )

    # --- edges: citations -----------------------------------------------------
    if citations:
        for c in citations:
            s = c["source"]
            t = c["target"]
            p = c["predicate"]

            # keep only if both works are in current filtered set
            if s not in work_uris or t not in work_uris:
                continue

            edges.append(
                Edge(
                    source=s,
                    target=t,
                    label=replace_prefixes_if_uri(p),
                    color=get_edge_color(p),
                    arrows_to=True,          # directed citation
                    type="STRAIGHT",
                    smooth=False,
                )
            )

    cfg = Config(
        width="100%",
        height=500,
        directed=True,
        nodes={"font": {"size": 10}},
        edges={"smooth": False},
        interaction={"hover": True},
    )

    clicked = agraph(nodes=nodes, edges=edges, config=cfg)
    return clicked



def build_layered_work_graph(
    is_skeleton: bool,
    rows: List[Dict],
    work_uri: str,
    expanded_classes: Dict[str, bool],
):
    """
    Two modes:
        1) Skeleton mode (title-only works)
        2) Full ontology skeleton + toggleable class expansion
    """

    # -------------------------------------------------
    # 0. Skeleton mode (title-only works)
    # -------------------------------------------------
    if is_skeleton:

        # extract a title literal if any
        title_literal = None
        for r in rows:
            p = r["p"]["value"]
            if "title" in p or "label" in p:
                title_literal = r["o"]["value"]
                break

        node = Node(
            id=work_uri,
            label=_local_name(work_uri),
            title=title_literal or work_uri,
            size=30,
            color="#FFFFFF",
            shape="box",
        )

        cfg = Config(width="100%", height=700, directed=True, physics=True)
        return agraph(nodes=[node], edges=[], config=cfg)

    # -------------------------------------------------
    # 1. FULL MODE — Ontology skeleton
    # -------------------------------------------------
    CLASS_COLOR = "#EEF2FF"
    nodes = {}
    edges = []

    # helper
    def add_class(iri, label):
        if iri == "idea:Artifact":
            cid = f"class:{label}"
        else:
            cid = f"class:{iri}"
        if cid not in nodes:
            nodes[cid] = Node(
                id=cid, label=label, title=iri,
                size=20, color=CLASS_COLOR, shape="ellipse"
            )
        return cid

    # ---- Ontology classes ----
    cid_work       = add_class("fabio:Work", "Work")
    cid_de         = add_class("deo:DiscourseElement", "DiscourseElement")
    cid_person     = add_class("foaf:Person", "Person")
    cid_event      = add_class("bibo:Event", "Event")
    cid_topic      = add_class("cso:Topic", "Topic")
    cid_argument   = add_class("amo:Argument", "Argument")

    cid_claim      = add_class("amo:Claim", "Claim")
    cid_backing    = add_class("amo:Backing", "Backing")
    cid_evidence   = add_class("amo:Evidence", "Evidence")
    cid_warrant    = add_class("amo:Warrant", "Warrant")

    cid_idea       = add_class("idea:Idea", "Idea")
    cid_issue      = add_class("idea:Issue", "Issue")
    cid_approach   = add_class("idea:Approach", "Approach")
    cid_assump     = add_class("idea:Assumption", "Assumption")
    cid_artifact_introduced   = add_class("idea:Artifact", "IntroducedArtifact")
    cid_artifact_used   = add_class("idea:Artifact", "UsedArtifact")

    def link(src, pred, dst):
        edges.append(Edge(source=src, target=dst, arrows_to=True, label=pred, color="#999"))

    # ---- Ontology links ----
    link(cid_work,     "po:contains",         cid_de)
    link(cid_work,     "dc:creator",          cid_person)
    link(cid_work,     "dc:publisher",        cid_event)
    link(cid_work,     "fabio:hasDiscipline", cid_topic)
    link(cid_work,     "amo:hasArgument",     cid_argument)

    link(cid_argument, "amo:hasClaim",        cid_claim)
    link(cid_argument, "amo:hasBacking",      cid_backing)
    link(cid_argument, "amo:hasEvidence",     cid_evidence)
    link(cid_argument, "amo:hasWarrant",      cid_warrant)
    link(cid_argument, "idea:proposesIdea",   cid_idea)
    link(cid_argument, "idea:concernsIssue",  cid_issue)
    link(cid_argument, "idea:realizes",       cid_approach)

    link(cid_approach, "idea:uses",           cid_artifact_used)
    link(cid_approach, "idea:introduces",     cid_artifact_introduced)
    link(cid_approach, "idea:hasAssumption",  cid_assump)

    link(cid_warrant, "amo:leadsTo", cid_claim)
    link(cid_idea, "idea:respondsTo", cid_issue)
    link(cid_approach, "idea:generates", cid_evidence)
    link(cid_evidence, "amo:supports", cid_claim)

    # -------------------------------------------------
    # 2. Add Work instance
    # -------------------------------------------------
    nodes[work_uri] = Node(
        id=work_uri,
        label=_local_name(work_uri),
        title=work_uri,
        size=25,
        color="#FFFFFF",
        shape="box",
    )
    edges.append(Edge(source=work_uri, target=cid_work, arrows_to=True, color="#000"))

    # -------------------------------------------------
    # 3. Map instance rows → classes
    # -------------------------------------------------
    CLASS_LIST = [
        "deo:DiscourseElement", "foaf:Person", "bibo:Event",
        "cso:Topic", "amo:Argument", "amo:Claim", "amo:Evidence",
        "amo:Backing", "amo:Warrant", "idea:Idea", "idea:Issue",
        "idea:Approach", "idea:Assumption", "idea:Artifact",
    ]

    class_instances = {cls: [] for cls in CLASS_LIST}

    def match(t, cls):
        return t.endswith(cls)

    for r in rows:
        s, o = r["s"]["value"], r["o"]["value"]
        st = r.get("sType", {}).get("value", "")
        ot = r.get("oType", {}).get("value", "")
        p  = r["p"]["value"]
        
        for cls in CLASS_LIST:
            if iri_matches_class(st, cls):
                class_instances[cls].append((s, r))
            if iri_matches_class(ot, cls):
                class_instances[cls].append((o, r))

        # --- 3.b PREDICATE-BASED FALLBACKS (this is the important fix) ---

        # Use CURIE-ish form of predicate so we can check by prefix:localName
        o_curie = replace_prefixes_if_uri(ot)
        p_curie = replace_prefixes_if_uri(p)
        # print(f"Processing predicate: {o_curie}")
        # po:contains ⇒ DiscourseElement
        deos = ['deo:abstract', 'deo:appendix', 'deo:background', 'deo:conclusion', 'deo:data', 'deo:discussion', 'deo:evaluation', 'deo:future_work', 'deo:introduction', 'deo:methodology', 'deo:model', 'deo:motivation', 'deo:related_work', 'deo:results']
        if o_curie in deos and is_resource(o):
            class_instances["deo:DiscourseElement"].append((o, r))

        # expos = ['expo:Design', 'expo:Hypothesis', 'expo:Results']
        # if o_curie in expos and is_resource(o):
        #     class_instances["deo:DiscourseElement"].append((o, r))

    # # fabio:hasDiscipline ⇒ Topic
    # if p_curie == "fabio:hasDiscipline" and is_resource(o):
    #     class_instances["cso:Topic"].append((o, r))

    # # idea:uses / idea:introduces ⇒ Artifact
    # if p_curie in ("idea:uses", "idea:introduces") and is_resource(o):
    #     class_instances["idea:Artifact"].append((o, r))

    # # idea:hasAssumption ⇒ Assumption
    # if p_curie == "idea:hasAssumption" and is_resource(o):
    #     class_instances["idea:Assumption"].append((o, r))

    # # amo:hasWarrant ⇒ Warrant
    # if p_curie == "amo:hasWarrant" and is_resource(o):
    #     class_instances["amo:Warrant"].append((o, r))

    # -------------------------------------------------
    # 4. Expand classes if toggled
    # -------------------------------------------------
    for cls, inst_rows in class_instances.items():
        cid = f"class:{cls}"
        # print(f"Cid: {cid}, class: {cls}")
        # if cid == "class:idea:Artifact":
        #     print("Linking Approach instance:", inst_rows)
        
        if expanded_classes.get("IntroducedArtifact", False) or expanded_classes.get("UsedArtifact", False):
            expanded_classes["idea:Artifact"] = True

        if expanded_classes.get(cls, False):

            if expanded_classes.get("idea:Artifact", False) and (expanded_classes.get("IntroducedArtifact", False) or expanded_classes.get("UsedArtifact", False)):
                expanded_classes.pop("idea:Artifact", None)

            for inst_uri, r in inst_rows:
                pred = r["p"]["value"].split("/")[-1]

                if inst_uri not in nodes:
                    if (expanded_classes.get("IntroducedArtifact", False) and pred == "uses") or (expanded_classes.get("UsedArtifact", False) and pred == "introduces"):
                        continue

                    label = r.get("label", {}).get("value", _local_name(inst_uri))
                    nodes[inst_uri] = Node(
                        id=inst_uri,
                        label=label[:25],
                        title=inst_uri,
                        size=14,
                        color="#D6F1FF",
                        shape="ellipse",
                    )
                
                if r["p"]["value"] == "http://www.semanticweb.org/idea/uses":
                    cid = "class:UsedArtifact"
                elif r["p"]["value"] == "http://www.semanticweb.org/idea/introduces":
                    print("running here....")
                    cid = "class:IntroducedArtifact"
                # else:
                #     cid = f"class:{cls}"
                
                if (expanded_classes.get("IntroducedArtifact", False) and pred == "used") or (expanded_classes.get("UsedArtifact", False) and pred == "introduced"):
                        continue
                edges.append(Edge(
                    source=cid,
                    target=inst_uri,
                    arrows_to=True,
                    color="#66A",
                ))

    # -------------------------------------------------
    # 5. Render
    # -------------------------------------------------
    cfg = Config(
        width="100%",
        height=700,
        directed=True,
        interaction={"hover": True},

        physics={
            "enabled": True,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springConstant": 0.08,
                "springLength": 150,   # ← pushes nodes apart
                "avoidOverlap": 1      # ← ESSENTIAL to prevent overlaps
            },
            "minVelocity": 0.75
        },

        layout={
            "hierarchical": False
        }
    )

    return agraph(nodes=list(nodes.values()), edges=edges, config=cfg)
