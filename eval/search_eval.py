import argparse
from pathlib import Path

import yaml
from sqlalchemy import select

from app.db.models import Product, Store
from app.db.session import SessionLocal
from app.schemas.search import SearchFilters
from app.services.search import search_products

K = 5


def main():
    parser = argparse.ArgumentParser(description="Оценка поиска: recall@5 и MRR")
    parser.add_argument("--store", required=True)
    parser.add_argument("--file", default="eval/golden_search.yaml")
    args = parser.parse_args()

    golden = yaml.safe_load(Path(args.file).read_text(encoding="utf-8"))

    with SessionLocal() as db:
        store = db.scalar(select(Store).where(Store.name == args.store))
        titles = {p.title: p.id for p in db.scalars(select(Product).where(Product.store_id == store.id))}

        missing = [g["target"] for g in golden if g["target"] not in titles]
        if missing:
            raise SystemExit(f"Нет таких товаров в каталоге (проверь title): {missing}")

        # оцениваем качество поиска, а не наличие на складе → in_stock_only=False
        filters = SearchFilters(in_stock_only=False)

        print(f"{'Режим':<16} {'язык':<5} {'recall@5':>9} {'MRR':>6}")
        for use_rerank in (False, True):
            stats = {"az": [], "ru": []}  # для каждого языка — список рангов (None = не найден)
            for g in golden:
                target_id = titles[g["target"]]
                for lang in ("az", "ru"):
                    hits = search_products(db, store.id, g[lang], filters, k=K, use_rerank=use_rerank)
                    ids = [h.product_id for h in hits]
                    rank = ids.index(target_id) + 1 if target_id in ids else None
                    stats[lang].append(rank)
                    if rank is None:
                        print(f"   ✗ [{lang}] «{g[lang]}» → не найден {g['target']}")

            mode = "с re-ranking" if use_rerank else "без re-ranking"
            for lang in ("az", "ru", "все"):
                ranks = stats["az"] + stats["ru"] if lang == "все" else stats[lang]
                n = len(ranks)
                if n == 0:  # защита от деления на ноль, если список пустой
                    recall = mrr = 0.0
                else:
                    recall = sum(1 for r in ranks if r is not None) / n
                    mrr = sum(1 / r if r is not None else 0 for r in ranks) / n
                print(f"{mode:<16} {lang:<5} {recall:>9.2f} {mrr:>6.2f}")

if __name__ == "__main__":
    main()