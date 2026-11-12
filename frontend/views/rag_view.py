"""Search source-backed regulatory documents."""

import streamlit as st

from app.modules.rag.assistant import answer_regulatory_query
from app.schemas.rag import RAGQueryRequest


def render_rag_view() -> None:
    st.subheader("Regulatory document search")
    st.caption("The assistant retrieves source text only. This build contains no bundled regulatory documents.")
    st.info("Add official source documents with title, publication year, and URL metadata to data/regulatory_docs, then rebuild the index before querying.")

    query = st.text_input(
        "Question",
        placeholder="Enter a CBAM question to search the indexed source documents",
    )
    if st.button("Search indexed documents", type="primary", disabled=not query.strip()):
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
