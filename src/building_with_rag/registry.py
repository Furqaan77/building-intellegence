from building_with_rag.models import QueryRequest, QueryResult

# The single source of truth for course modes: mode name -> OpenAI-style model ID.
MODE_REGISTRY: dict[str, str] = {
    "semantic": "rag-semantic",
    "hybrid": "rag-hybrid",
    "hybrid-reranked": "rag-hybrid-reranked",
    "structured": "rag-structured",
    "decomposition": "rag-decomposition",
    "hyde": "rag-hyde",
}

MODEL_TO_MODE: dict[str, str] = {model_id: mode for mode, model_id in MODE_REGISTRY.items()}


def run_pattern(request: QueryRequest) -> QueryResult:
    """Run the requested mode. Every mode is a placeholder in Story 1.1."""
    return QueryResult(
        pattern=request.pattern,
        status="not_implemented",
        message=f"The '{request.pattern}' mode is not implemented yet.",
        results=[],
    )
