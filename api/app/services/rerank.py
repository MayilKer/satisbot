import voyageai

from app.config import settings

_client = voyageai.Client(api_key=settings.voyage_api_key)


def rerank(query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
    """Возвращает [(индекс документа, оценка релевантности)] от лучшего к худшему."""
    result = _client.rerank(query, documents, model=settings.rerank_model, top_k=top_k)
    return [(r.index, r.relevance_score) for r in result.results]