import streamlit as st
from streamlit_agraph import agraph, Config
from core.graph_builder import triples_to_graph

def show_graph(triples, height=800):
    nodes, edges = triples_to_graph(triples)

    config = Config(
        width="100%",
        height=height,
        directed=True,
        physics=True,
        hierarchical=False
    )

    st.subheader("Graph View")
    clicked = agraph(nodes=nodes, edges=edges, config=config)

    # agraph returns the clicked node ID (URI)
    return clicked