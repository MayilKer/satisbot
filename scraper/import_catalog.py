import argparse
from dataclasses import asdict

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.db.models import Product, Store
from app.db.session import SessionLocal
from scraper.adapters.base import ProductData
from scraper.adapters.mssql import MssqlAdapter
from scraper.adapters.shopify import ShopifyAdapter

import random
from decimal import Decimal

ADAPTERS = {"shopify": ShopifyAdapter}


def get_adapter(store: Store):
    if store.source_type == "mssql":
        return MssqlAdapter(env_var=store.source_url)
    adapter_cls = ADAPTERS.get(store.source_type)
    if adapter_cls is None:
        raise ValueError(f"Нет адаптера для source_type={store.source_type!r}")
    return adapter_cls(store.source_url)


def upsert_product(db, store_id: int, p: ProductData) -> None:
    values = {"store_id": store_id, **asdict(p)}
    stmt = insert(Product).values(**values)
    update_cols = {k: stmt.excluded[k] for k in values if k not in ("store_id", "external_id")}
    update_cols["scraped_at"] = func.now()
    stmt = stmt.on_conflict_do_update(
        index_elements=["store_id", "external_id"], set_=update_cols
    )
    db.execute(stmt)

BASE_RANGE = {"EDC": (40, 90), "EDT": (80, 200), "EDP": (120, 320), "Parfum": (200, 480)}
DEFAULT_RANGE = (100, 280)


def demo_price(store_id: int, p: Product) -> tuple[Decimal, Decimal | None]:
    rnd = random.Random(f"{store_id}:{p.external_id}")            # один и тот же результат при каждом запуске
    brand_factor = random.Random(f"brand:{p.brand}").uniform(0.85, 1.5)  # один бренд — один ценовой уровень
    low, high = BASE_RANGE.get((p.attributes or {}).get("concentration"), DEFAULT_RANGE)
    price = round(rnd.uniform(low, high) * brand_factor / 10) * 10 - 1  # 149, 189, 229…
    old_price = None
    if rnd.random() < 0.15:  # ~15% товаров «со скидкой»
        old_price = Decimal(round(price * rnd.uniform(1.15, 1.35) / 10) * 10 - 1)
    return Decimal(price), old_price


def fill_demo_prices(db, store_id: int) -> int:
    products = db.scalars(
        select(Product).where(Product.store_id == store_id, Product.price_azn.is_(None))
    ).all()
    for p in products:
        p.price_azn, p.old_price_azn = demo_price(store_id, p)
        p.attributes = {**(p.attributes or {}), "price_is_demo": True}
    db.commit()
    return len(products)

def main():
    parser = argparse.ArgumentParser(description="Импорт каталога магазина")
    parser.add_argument("--store", required=True, help="Название магазина из таблицы stores")
    parser.add_argument("--demo-prices", action="store_true",
                        help="Заполнить пустые цены демо-значениями (только для портфолио)")
    args = parser.parse_args()

    with SessionLocal() as db:
        store = db.scalar(select(Store).where(Store.name == args.store))
        if store is None:
            raise SystemExit(f"Магазин {args.store!r} не найден")

        adapter = get_adapter(store)
        count = 0
        for p in adapter.fetch_products():
            upsert_product(db, store.id, p)
            count += 1
            if count % 100 == 0:
                db.commit()
                print(f"Сохранено: {count}")
        db.commit()
        print(f"Готово. Импортировано товаров: {count}")
        if args.demo_prices:
            filled = fill_demo_prices(db, store.id)
            print(f"Демо-цены проставлены: {filled}")


if __name__ == "__main__":
    main()