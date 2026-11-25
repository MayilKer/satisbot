from app.services.embeddings import embed_query
from app.services.vectors import FAQ, client, store_filter


def search_faq(store_id: int, question: str, k: int = 3) -> list[dict]:
    hits = client.query_points(
        collection_name=FAQ,
        query=embed_query(question),
        query_filter=store_filter(store_id),
        limit=k,
        with_payload=True,
    ).points
    return [
        {
            "question": h.payload["question"],
            "answer": h.payload["answer"],
            "lang": h.payload["lang"],
            "score": round(h.score, 3),
        }
        for h in hits
    ]