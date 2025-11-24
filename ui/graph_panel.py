import streamlit as st
from streamlit_agraph import agraph, Config
from core.graph_builder import triples_to_graph
from html import escape

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

def render_legend(style_dict, title="Legend"):
    """
    style_dict: {
        "Work": "#FFFFFF",
        "Person": "#A0C3FF",
        "Claim": "#FFE8A3",
        ...
    }
    """

    items_html = ""

    for label, color in style_dict.items():
        # Optional: detect if white background => add border
        border = "border:1px solid #000;" if color.upper() in ("#FFFFFF", "#FFFFFFD3") else ""

        items_html += f"""
    <div><span style="background:{escape(color)}; {border} padding:4px 8px;">{escape(label)}</span></div>
        """

    full_html = f"""
    <div style="display:flex; flex-wrap:wrap; gap:12px; align-items:center;">
    {items_html}
    </div>
    """
    st.markdown("### Legend")
    st.markdown(full_html, unsafe_allow_html=True)