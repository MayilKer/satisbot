import argparse

from qdrant_client import models
from sqlalchemy import select

from app.db.models import FAQ, Product, Store
from app.db.session import SessionLocal
from app.services.cache import delete_prefix
from app.services.embeddings import embed_documents, embed_query
from app.services.product_text import product_text
from app.services.vectors import (
    FAQ as FAQ_COLLECTION, FAQ_INDEXES, PRODUCT_INDEXES, PRODUCTS,
    client, ensure_collection, store_filter,
)

UPSERT_BATCH = 256


def product_payload(p: Product) -> dict:
    attrs = p.attributes or {}
    return {
        "store_id": p.store_id,
        "product_id": p.id,
        "title": p.title,
        "brand": p.brand,
        "gender": attrs.get("gender"),
        "concentration": attrs.get("concentration"),
        "release_year": attrs.get("release_year"),
        "price_azn": float(p.price_azn) if p.price_azn is not None else None,
        "in_stock": p.in_stock,
    }


def upsert(collection: str, points: list[models.PointStruct]) -> None:
    for i in range(0, len(points), UPSERT_BATCH):
        client.upsert(collection_name=collection, points=points[i:i + UPSERT_BATCH])


def index_products(db, store: Store, dim: int) -> int:
    ensure_collection(PRODUCTS, dim, PRODUCT_INDEXES)
    products = db.scalars(select(Product).where(Product.store_id == store.id)).all()
    print(f"Товаров к индексации: {len(products)}")
    vectors = embed_documents([product_text(p) for p in products])

    points = []

    for p, v in zip(products, vectors):
        points.append(models.PointStruct(id=p.id, vector=v, payload=product_payload(p)))

    upsert(PRODUCTS, points)
    return len(points)


def index_faq(db, store: Store, dim: int) -> int:
    ensure_collection(FAQ_COLLECTION, dim, FAQ_INDEXES)
    items = db.scalars(select(FAQ).where(FAQ.store_id == store.id)).all()
    # FAQ загружается «заменой целиком», id меняются → сначала удаляем старые точки магазина
    client.delete(collection_name=FAQ_COLLECTION,
                  points_selector=models.FilterSelector(filter=store_filter(store.id)))
    vectors = embed_documents([f"{f.question}\n{f.answer}" for f in items])

    points = [
        models.PointStruct(
            id=f.id,
            vector=v,
            payload={
                "store_id": f.store_id,
                "faq_id": f.id,
                "lang": f.lang,
                "category": f.category,
                "question": f.question,
                "answer": f.answer,
            },
        )
        for f, v in zip(items, vectors)
    ]

    upsert(FAQ_COLLECTION, points)
    return len(points)


def main():
    parser = argparse.ArgumentParser(description="Индексация каталога и FAQ в Qdrant")
    parser.add_argument("--store", required=True)
    args = parser.parse_args()

    dim = len(embed_query("dimension probe"))  # размер вектора узнаём у модели, а не хардкодим
    with SessionLocal() as db:
        store = db.scalar(select(Store).where(Store.name == args.store))
        if store is None:
            raise SystemExit(f"Магазин {args.store!r} не найден")
        n_products = index_products(db, store, dim)
        n_faq = index_faq(db, store, dim)

    in_qdrant = client.count(PRODUCTS, count_filter=store_filter(store.id), exact=True).count
    print(f"Готово. Товаров: {n_products} (в Qdrant: {in_qdrant}), FAQ: {n_faq}")
    removed = delete_prefix(f"search:{store.id}:")
    print(f"Сброшено ключей кэша поиска: {removed}")


if __name__ == "__main__":
    main()
