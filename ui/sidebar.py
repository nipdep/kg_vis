import streamlit as st
from core.resource_inspector import search_paper_by_title, get_venues, get_years

def sidebar_controls(endpoint):
    st.sidebar.header("Paper Search / Filters")

    # Search by title
    title = st.sidebar.text_input("Search paper by title")
    selected_paper = None

    if title:
        results = search_paper_by_title(endpoint, title)
        options = [r["paper"]["value"] for r in results]
        selected_paper = st.sidebar.selectbox("Matches", options)

    # Filter by venue
    venues = [v["venue"]["value"] for v in get_venues(endpoint)]
    venue = st.sidebar.selectbox("Filter by Venue", [""] + venues)

    # Filter by year
    years = [y["year"]["value"] for y in get_years(endpoint)]
    year = st.sidebar.selectbox("Filter by Year", [""] + years)

    return selected_paper, venue, year
