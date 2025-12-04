import streamlit as st

from config.settings import PAGE_TITLE, PAGE_ICON, IDEA_ENDPOINT

# old features preserved
from ui.sidebar import sidebar_controls

# new graph logic
from ui.work_viewer import build_work_overview_graph, build_layered_work_graph
# from ui.work_viewer_pyviz import build_layered_work_graph
from core.work_graph import (
    get_all_works,
    get_work_local_graph,
    get_top_keywords,
    get_citation_edges
    )
from ui.graph_panel import render_legend
from ui.styling import legend_styles
from core.resource_inspector import get_resource_properties
from core.query_builder import replace_prefixes_if_uri

# -----------------------------------------------------------
# Streamlit setup
# -----------------------------------------------------------
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
st.title(PAGE_TITLE)

sparql_endpoint = IDEA_ENDPOINT


# -----------------------------------------------------------
# SIDEBAR SEARCH (restored)
# -----------------------------------------------------------
st.sidebar.header("Search Papers")
search_title, search_venue, search_year = sidebar_controls(IDEA_ENDPOINT)

st.sidebar.markdown("---")
st.sidebar.subheader("Keyword cloud")

try:
    top_keywords = get_top_keywords(sparql_endpoint, limit=30)
except Exception:
    top_keywords = []

if top_keywords:
    # simple inline "cloud"
    kw_chunks = []
    for kw in top_keywords:
        uri = kw["uri"]
        label = replace_prefixes_if_uri(uri)
        # strip idea:/cso: prefixes visually
        for prefix in ("idea:", "cso:"):
            if label.startswith(prefix):
                label = label[len(prefix):]
        label = label.replace("_", " ")
        kw_chunks.append(f"`{label}`")
    st.sidebar.markdown(" ".join(kw_chunks))
else:
    st.sidebar.caption("No keywords found (or query failed).")

# -----------------------------------------------------------
# SESSION STATE — selected work
# -----------------------------------------------------------

if "selected_work" not in st.session_state:
    st.session_state["selected_work"] = None

if "expanded_classes" not in st.session_state:
    st.session_state["expanded_classes"] = {}

# IMPORTANT: must be initialized before first access
if "last_clicked_node" not in st.session_state:
    st.session_state["last_clicked_node"] = None

# -----------------------------------------------------------
# 1. OVERVIEW LIST (filtered by sidebar)
# -----------------------------------------------------------
st.markdown("## All Publications")

# Load all works
works = get_all_works(sparql_endpoint)
# citations = get_work_citations(sparql_endpoint)

# Apply search filtering
def passes_filters(w):
    label = w["label"].lower()
    year = w["year"]

    if search_title and search_title.lower() not in label:
        return False
    if search_venue and search_venue.lower() not in label:
        return False
    if search_year and year != search_year:
        return False
    return True

filtered_works = [w for w in works if passes_filters(w)]
st.caption(f"{len(filtered_works)} works found")

# build overview graph
citations = get_citation_edges(sparql_endpoint)
print("CITATIONS:", len(citations))
clicked_work = build_work_overview_graph(filtered_works, citations=citations)

if clicked_work:
    st.session_state["selected_work"] = clicked_work

selected_work = st.session_state["selected_work"]


# -----------------------------------------------------------
# 2. DETAILED WORK VIEW
# -----------------------------------------------------------
if selected_work:

    st.markdown("---")
    st.markdown(
        f"## Work-centric View for: **`{replace_prefixes_if_uri(selected_work)}`**"
    )
    # render_legend(legend_styles)

    # toggles
    # col1, col2, col3 = st.columns([1, 1, 1])
    # with col1:
    #     show_structure = st.toggle("Show Structure", value=True)
    # with col2:
    #     show_argument = st.toggle("Show Argument", value=True)
    # with col3:
    #     show_metadata = st.toggle("Show Metadata", value=True)

    # pull graph from SPARQL
    is_skeleton, work_rows = get_work_local_graph(
        sparql_endpoint,
        selected_work,
    )

    # print("Work rows:",work_rows)
    # build graph nodes/edges
    print("Expanded classes:", st.session_state["expanded_classes"])
    clicked_node = build_layered_work_graph(
        is_skeleton=is_skeleton,
        rows=work_rows,
        work_uri=selected_work,
        expanded_classes=st.session_state["expanded_classes"]
    )

     # -------------------------------------------------------
    # DETAILS
    # -------------------------------------------------------

    # -----------------------
    # Node details (table)
    # -----------------------
    st.markdown("---")
    st.markdown("### Node Details")

    # target_uri = clicked_node or selected_work
    if clicked_node:
        if clicked_node.startswith("class:"):
            target_uri = clicked_node.replace("class:", "")
        else:
            target_uri = clicked_node
    elif selected_work:
        target_uri = selected_work
    else:
        target_uri = None

    print("clicked_node:", clicked_node, "target_uri:", target_uri, "selected_work:", selected_work)
    st.write(f"**Selected Node:** `{replace_prefixes_if_uri(target_uri)}`")

    rows = get_resource_properties(sparql_endpoint, target_uri)
    # print("Resource properties rows:", rows)
    st.dataframe(
        [{"property": replace_prefixes_if_uri(r["p"]["value"]),
          "value": r["o"]["value"]}
         for r in rows],
        use_container_width=True,
        height=350
    )


    if clicked_node != st.session_state["last_clicked_node"]:
        st.session_state["last_clicked_node"] = clicked_node

        if clicked_node and clicked_node.startswith("class:"):
            class_iri = clicked_node.replace("class:", "")
            st.session_state["expanded_classes"][class_iri] = (
                not st.session_state["expanded_classes"].get(class_iri, False)
            )
            st.rerun()
   
else:
    st.info("Click a paper node above to open the work-centric view.")
