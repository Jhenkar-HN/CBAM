"""Search source-backed regulatory documents."""

import streamlit as st

from app.modules.rag.assistant import answer_regulatory_query
from app.schemas.rag import RAGQueryRequest
from frontend.ui import page_header


def render_rag_view() -> None:
    page_header(
        "Regulatory assistant",
        "Search CBAM regulations",
        "Retrieves verbatim source text with citations from the indexed regulatory documents. It never generates legal advice.",
    )
    st.info("Add official source documents with title, publication year, and URL metadata to data/regulatory_docs, then rebuild the index before querying.")

    with st.form("rag_query", border=False):
        query_col, button_col = st.columns([5, 1], vertical_alignment="bottom")
        query = query_col.text_input(
            "Question",
            placeholder="e.g. Which emissions must be included for CN 7318 fasteners?",
        )
        submitted = button_col.form_submit_button("Search", type="primary", use_container_width=True)
    if submitted and query.strip():
        result = answer_regulatory_query(RAGQueryRequest(query=query.strip(), top_k=3))
        st.markdown("### Retrieved source text")
        st.info(result.answer)
        if result.citations:
            st.markdown("#### Citations")
            for index, citation in enumerate(result.citations, start=1):
                year = citation.publication_year or "Year not recorded"
                with st.expander(f"{index}. {citation.document_title} · {citation.section_reference} · {year}"):
                    if citation.source_url:
                        st.markdown(f"[Open source document]({citation.source_url})")
                    st.caption(f"Similarity score: {citation.score:.4f}")
                    st.markdown(f"> {citation.excerpt}")
