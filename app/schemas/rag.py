from typing import List, Optional
from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    query: str = Field(..., json_schema_extra={"example": "What are the rules for precursor emissions for steel fasteners under CN 7318?"})
    top_k: int = Field(default=3, ge=1, le=10)
    cn_code_filter: Optional[str] = Field(None, json_schema_extra={"example": "7318 15 82"})


class RAGCitation(BaseModel):
    document_title: str = Field(..., json_schema_extra={"example": "Guidance document on CBAM implementation for installation operators"})
    section_reference: str = Field(..., json_schema_extra={"example": "Section 6.4: Rules for Complex Goods (Fasteners)"})
    publication_year: int = Field(default=2024)
    excerpt: str = Field(..., description="Verbatim cited text excerpt from official EU documentation")
    score: float = Field(..., description="Cosine similarity score")


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[RAGCitation] = Field(default_factory=list)
