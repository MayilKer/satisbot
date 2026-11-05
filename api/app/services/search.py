from qdrant_client import models
from sqlalchemy import select

from app.db.models import Product
from app.schemas.search import ProductHit, SearchFilters
from app.services.cache import get_json, make_key, normalize, set_json
from app.services.embeddings import embed_query
from app.services.product_text import product_text
from app.services.rerank import rerank
from app.services.vectors import PRODUCTS, client

SEARCH_TTL = 600  # 10 минут


def build_filter(store_id: int, f: SearchFilters) -> models.Filter:
    must = [models.FieldCondition(key="store_id", match=models.MatchValue(value=store_id))]
    if f.in_stock_only:
        must.append(models.FieldCondition(key="in_stock", match=models.MatchValue(value=True)))
    if f.concentration:
        must.append(models.FieldCondition(key="concentration", match=models.MatchValue(value=f.concentration)))
    if f.gender:
        if f.include_unisex and f.gender != "unisex":
            must.append(models.FieldCondition(key="gender", match=models.MatchAny(any=[f.gender, "unisex"])))
        else:
            must.append(models.FieldCondition(key="gender", match=models.MatchValue(value=f.gender)))
    if f.min_price is not None or f.max_price is not None:
        must.append(models.FieldCondition(key="price_azn", range=models.Range(gte=f.min_price, lte=f.max_price)))
    return models.Filter(must=must)


def to_hit(p: Product, score: float) -> ProductHit:
    attrs = p.attributes or {}
    return ProductHit(
        product_id=p.id,
        title=p.title,
        brand=p.brand,
        price_azn=float(p.price_azn) if p.price_azn is not None else None,
        old_price_azn=float(p.old_price_azn) if p.old_price_azn is not None else None,
        price_is_demo=bool(attrs.get("price_is_demo")),
        in_stock=p.in_stock,
        gender=attrs.get("gender"),
        concentration=attrs.get("concentration"),
        image_url=(p.image_urls or [None])[0],
        score=score,
    )


def _search_ids(db, store_id: int, query: str, filters: SearchFilters,
                k: int, candidates: int, use_rerank: bool) -> list[list]:
    hits = client.query_points(
        collection_name=PRODUCTS,
        query=embed_query(query),
        query_filter=build_filter(store_id, filters),
        limit=candidates,
        with_payload=False,
    ).points
    if not hits:
        return []
    ids = [h.id for h in hits]
    if use_rerank and len(ids) > 1:
        by_id = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids))).all()}
        products = [by_id[i] for i in ids if i in by_id]
        ranked = rerank(query, [product_text(p) for p in products], top_k=k)
        return [[products[i].id, score] for i, score in ranked]
    return [[h.id, h.score] for h in hits[:k]]


def search_products(db, store_id: int, query: str, filters: SearchFilters,
                    k: int = 5, candidates: int = 20, use_rerank: bool = True) -> list[ProductHit]:
    key = make_key(f"search:{store_id}", normalize(query), filters.model_dump(), k, candidates, use_rerank)

    ranked = get_json(key)
    if ranked is None:
        ranked = _search_ids(db, store_id, query, filters, k, candidates, use_rerank)
        set_json(key, ranked, ttl=SEARCH_TTL)
    if not ranked:
        return []

    # свежие данные из Postgres — даже если id взяты из кэша
    ids = [pid for pid, _ in ranked]
    by_id = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(ids))).all()}
    return [to_hit(by_id[pid], score) for pid, score in ranked if pid in by_id]
