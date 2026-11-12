from typing import List, Optional
from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=3, ge=1, le=10)
    cn_code_filter: Optional[str] = None


class RAGCitation(BaseModel):
    document_title: str
    section_reference: str
    publication_year: Optional[int] = None
    source_url: Optional[str] = None
    excerpt: str = Field(..., description="Verbatim cited text excerpt from official EU documentation")
    score: float = Field(..., description="Cosine similarity score")


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[RAGCitation] = Field(default_factory=list)
