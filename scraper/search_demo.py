import argparse
import time  # ← новое

from sqlalchemy import select

from app.db.models import Store
from app.db.session import SessionLocal
from app.schemas.search import SearchFilters
from app.services.search import search_products


def main():
    parser = argparse.ArgumentParser(description="Проверка поиска товаров")
    parser.add_argument("query")
    parser.add_argument("--store", required=True)
    parser.add_argument("--gender", choices=["female", "male", "unisex"])
    parser.add_argument("--concentration", choices=["EDP", "EDT", "EDC", "Parfum"])
    parser.add_argument("--max-price", type=float)
    parser.add_argument("--no-rerank", action="store_true")
    args = parser.parse_args()

    filters = SearchFilters(gender=args.gender, concentration=args.concentration, max_price=args.max_price)
    with SessionLocal() as db:
        store = db.scalar(select(Store).where(Store.name == args.store))
        start = time.perf_counter()  # ← новое: засекаем время
        hits = search_products(db, store.id, args.query, filters, use_rerank=not args.no_rerank)
        elapsed = time.perf_counter() - start  # ← новое: сколько прошло

    mode = "без re-ranking" if args.no_rerank else "с re-ranking"
    print(f"\n🔎 «{args.query}» {filters.model_dump(exclude_defaults=True)} — {mode}")
    for i, h in enumerate(hits, 1):
        sale = f" (было {h.old_price_azn:.0f})" if h.old_price_azn else ""
        print(
            f"{i}. {h.score:.3f}  {h.title} | {h.brand} | {h.gender} | {h.concentration} | {h.price_azn:.0f} AZN{sale}")
    print(f"⏱ {elapsed:.3f} с")  # ← новое: печатаем время


if __name__ == "__main__":
    main()
