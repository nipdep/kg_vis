import streamlit as st

from config.settings import PAGE_TITLE, PAGE_ICON, IDEA_ENDPOINT

# old features preserved
from ui.sidebar import sidebar_controls
from ui.graph_panel import show_graph

# new graph logic
from ui.work_viewer import (
    build_work_overview_graph,
    build_layered_work_graph
)
from core.work_graph import (
    get_all_works,
    get_work_local_graph
)

from core.query_builder import replace_prefixes_if_uri
from core.sparql_client import execute_query_convert
from streamlit_agraph import agraph, Config


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


# -----------------------------------------------------------
# SESSION STATE — selected work
# -----------------------------------------------------------
if "selected_work" not in st.session_state:
    st.session_state["selected_work"] = None


# -----------------------------------------------------------
# 1. OVERVIEW LIST (filtered by sidebar)
# -----------------------------------------------------------
st.markdown("## All Publications")

# Load all works
works = get_all_works(sparql_endpoint)

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
clicked_work = build_work_overview_graph(filtered_works)

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

    # toggles
    col1, col2 = st.columns([1, 1])
    with col1:
        show_structure = st.toggle("Show Structure", value=True)
    with col2:
        show_argument = st.toggle("Show Argument", value=True)

    # pull graph from SPARQL
    work_rows = get_work_local_graph(
        sparql_endpoint,
        selected_work,
        # expand_arguments=True
    )

    # build graph nodes/edges
    work_nodes, work_edges = build_layered_work_graph(
        work_rows,
        work_uri=selected_work,
        show_structure=show_structure,
        show_argument=show_argument
    )

    # render
    cfg = Config(
        width="100%",
        height=700,
        directed=True,
        interaction={"hover": True},
        nodes={"font": {"size": 10}},
        edges={"font": {"size": 8}},
    )

    clicked_node = agraph(nodes=work_nodes, edges=work_edges, config=cfg)

    # -------------------------------------------------------
    # DETAILS
    # -------------------------------------------------------
    st.markdown("### Node Details")

    target_uri = clicked_node or selected_work

    st.write(f"**Selected Node:** `{replace_prefixes_if_uri(target_uri)}`")

    details_query = f"""
    SELECT ?p ?o WHERE {{
        <{target_uri}> ?p ?o .
    }}
    """
    rows = execute_query_convert(sparql_endpoint, details_query)

    st.dataframe(
        [{"property": replace_prefixes_if_uri(r["p"]["value"]),
          "value": r["o"]["value"]}
         for r in rows],
        use_container_width=True,
        height=350
    )

else:
    st.info("Click a paper node above to open the work-centric view.")
