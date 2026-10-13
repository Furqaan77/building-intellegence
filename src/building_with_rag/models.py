"""Shared typed contracts. Later stories extend these additively."""

from typing import Any, Literal

from pydantic import BaseModel, Field

Pattern = Literal["semantic", "hybrid", "hybrid-reranked", "structured", "decomposition", "hyde"]


class SemanticFilters(BaseModel):
    act: list[str] = Field(default_factory=list)
    status: list[str] = Field(default_factory=list)
    access_level: list[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    pattern: Pattern
    caller_id: str | None = None
    filters: SemanticFilters | None = None
    limit: int = Field(default=5, ge=1, le=20)
    generate_answer: bool = False
    required_acts: list[str] = Field(default_factory=list)
    chapter: str | None = None


class RetrievedChunk(BaseModel):
    chunk_id: str
    section_id: str
    act: str
    text: str
    heading: str | None = None
    score: float | None = None
    source: dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    outcome: Literal["answered", "insufficient_evidence", "unavailable", "malformed"]
    answer: str | None = None
    claims: list[Any] = Field(default_factory=list)
    citations: list[Any] = Field(default_factory=list)
    supporting_passages: list[RetrievedChunk] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    trace: list[Any] = Field(default_factory=list)
    context_outcome: str | None = None
    confidence: float | str | None = None
    draft_answer: str | None = None
    issues: list[Any] = Field(default_factory=list)
    attempts: int | list[Any] | None = None
    low_confidence_reason: str | None = None


class OmittedCandidate(BaseModel):
    chunk_id: str
    omitted_reason: str


class SubquestionEvidence(BaseModel):
    subquestion: str
    status: Literal["evidenced", "no_evidence"]
    results: list[RetrievedChunk] = Field(default_factory=list)
    reason: str | None = None


class StructuredSignals(BaseModel):
    intent: Literal["exact_lookup", "filter", "aggregation"]
    act: str | None = None
    section_number: str | None = None
    chapter: str | None = None


class QueryResult(BaseModel):
    pattern: Pattern
    status: str
    message: str
    trace: list[Any] = Field(default_factory=list)
    results: list[RetrievedChunk] = Field(default_factory=list)
    generation: GenerationResult | None = None
    omitted_candidates: list[OmittedCandidate] = Field(default_factory=list)
    subquestions: list[SubquestionEvidence] = Field(default_factory=list)
    hyde_direct_candidates: list[RetrievedChunk] = Field(default_factory=list)
    hyde_query_candidates: list[RetrievedChunk] = Field(default_factory=list)
    hyde_hypothetical_text_debug: str | None = None
