import time

import voyageai
from voyageai.error import RateLimitError

from app.config import settings

from app.services.cache import get_json, make_key, normalize, set_json

_client = voyageai.Client(api_key=settings.voyage_api_key)
BATCH = 128


def _embed(texts: list[str], model: str, input_type: str) -> list[list[float]]:
    for attempt in range(1, 6):
        try:
            return _client.embed(texts, model=model, input_type=input_type).embeddings
        except RateLimitError:
            wait = 20 * attempt
            print(f"Voyage: лимит запросов, жду {wait} с (попытка {attempt}/5)")
            time.sleep(wait)
    raise RuntimeError("Voyage: лимит запросов не снимается после 5 попыток")


def embed_documents(texts: list[str], model: str | None = None) -> list[list[float]]:
    model = model or settings.embedding_model
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        vectors.extend(_embed(texts[i:i + BATCH], model, "document"))
    return vectors


def embed_query(text: str, model: str | None = None) -> list[float]:
    model = model or settings.embedding_model
    key = make_key(f"emb:{model}", normalize(text))  # модель в ключе: другая модель — другие векторы
    cached = get_json(key)
    if cached is not None:
        return cached
    vector = _embed([text], model, "query")[0]
    set_json(key, vector, ttl=24 * 3600)
    return vector