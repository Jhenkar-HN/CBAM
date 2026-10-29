"""Regulatory RAG Assistant View."""

import streamlit as st
from app.modules.rag.assistant import answer_regulatory_query
from app.schemas.rag import RAGQueryRequest


SAMPLE_QUERIES = [
    "What are the rules for precursor emissions for steel fasteners under CN 7318?",
    "Which electricity emission factor must Indian exporters use under CBAM?",
    "What is the penalty markup for using EU default fallback values?",
    "How should unmetered shared facility energy be allocated between products?",
    "Does an internal emissions passport replace an accredited independent verifier?",
]


def render_rag_view():
    st.subheader("📚 European Commission Regulatory RAG Assistant")
    st.caption("Grounded intelligence assistant indexed against official EU CBAM Implementing Regulations (EU) 2023/956, 2025/2621, and sector guidance for complex steel goods.")

    # Sample query chips
    st.markdown("##### 💡 Suggested Questions")
    chip_cols = st.columns(len(SAMPLE_QUERIES))
    selected_sample = None
    for idx, q_text in enumerate(SAMPLE_QUERIES):
        with chip_cols[idx]:
            if st.button(f"Q{idx+1}: {q_text[:30]}...", key=f"q_btn_{idx}", help=q_text, use_container_width=True):
                selected_sample = q_text

    query_input = st.text_input(
        "Ask a regulatory question grounded in official EU CBAM documentation:",
        value=selected_sample if selected_sample else "",
        placeholder="e.g. What are the rules for precursor materials in steel fasteners?",
    )

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        submit_btn = st.button("🔍 Search Regulatory Index", type="primary", use_container_width=True)

    if submit_btn and query_input.strip():
        with st.spinner("Searching FAISS index and generating grounded citations..."):
            req = RAGQueryRequest(query=query_input.strip(), top_k=3)
            resp = answer_regulatory_query(req)

            st.markdown("---")
            st.markdown("### 📋 Regulatory Guidance Answer")
            st.info(resp.answer)

            if resp.citations:
                st.markdown("#### 📖 Grounded European Commission Citations")
                for idx, cit in enumerate(resp.citations):
                    with st.expander(f"Citation {idx+1}: {cit.document_title} | {cit.section_reference} ({cit.publication_year})", expanded=True):
                        st.markdown(f"**Section / Article:** `{cit.section_reference}`")
                        st.markdown(f"**Similarity Score:** `{cit.score:.4f}`")
                        st.markdown(f"**Verbatim Excerpt:**\n\n> {cit.excerpt}")
            else:
                st.warning("No official citation passages met the minimum confidence threshold.")
