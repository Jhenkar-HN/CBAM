"""Regulatory Q&A restricted to passages in indexed source documents."""

from typing import List

from app.modules.rag.indexer import get_vector_store
from app.schemas.rag import RAGCitation, RAGQueryRequest, RAGQueryResponse

SIMILARITY_THRESHOLD = 0.25


def answer_regulatory_query(request: RAGQueryRequest) -> RAGQueryResponse:
    """Return a retrieved source excerpt; do not synthesize unsupported legal claims."""
    store = get_vector_store()
    raw_results = store.search(request.query, top_k=request.top_k)
    valid_results = [(chunk, score) for chunk, score in raw_results if score >= SIMILARITY_THRESHOLD]

    if not valid_results:
        if not store.chunks:
            answer = (
                "No official regulatory source documents are indexed yet. Add current official documents to the regulatory document folder "
                "and rebuild the index before asking regulatory questions."
            )
        else:
            answer = "No passage relevant to this question was found in the indexed sources. Consult the official source document or an accredited verifier."
        return RAGQueryResponse(query=request.query, answer=answer, citations=[])

    citations: List[RAGCitation] = []
    excerpts: List[str] = []
    for chunk, score in valid_results:
        excerpt = chunk.text[:1000].strip()
        citations.append(
            RAGCitation(
                document_title=chunk.document_title,
                section_reference=chunk.section_reference,
                publication_year=chunk.publication_year,
                source_url=chunk.url,
                excerpt=excerpt,
                score=round(score, 4),
            )
        )
        excerpts.append(f"**{chunk.document_title} — {chunk.section_reference}**\n\n{excerpt}")

    answer = "Retrieved source passages (review the cited text directly):\n\n" + "\n\n---\n\n".join(excerpts)
    return RAGQueryResponse(query=request.query, answer=answer, citations=citations)
