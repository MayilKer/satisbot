from qdrant_client import QdrantClient, models

from app.config import settings

PRODUCTS = "products"
FAQ = "faq"

client = QdrantClient(url=settings.qdrant_url)

# поля, по которым будем фильтровать → payload-индексы
PRODUCT_INDEXES = {
    "store_id": models.PayloadSchemaType.INTEGER,
    "gender": models.PayloadSchemaType.KEYWORD,
    "concentration": models.PayloadSchemaType.KEYWORD,
    "brand": models.PayloadSchemaType.KEYWORD,
    "price_azn": models.PayloadSchemaType.FLOAT,
    "in_stock": models.PayloadSchemaType.BOOL,
}
FAQ_INDEXES = {
    "store_id": models.PayloadSchemaType.INTEGER,
    "lang": models.PayloadSchemaType.KEYWORD,
}


def ensure_collection(name: str, dim: int, indexes: dict) -> None:
    if not client.collection_exists(name):
        client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        print(f"Создана коллекция {name} (размер вектора {dim})")
    for field, schema in indexes.items():
        client.create_payload_index(collection_name=name, field_name=field, field_schema=schema)


def store_filter(store_id: int) -> models.Filter:
    return models.Filter(
        must=[models.FieldCondition(key="store_id", match=models.MatchValue(value=store_id))]
    )