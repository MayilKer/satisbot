import argparse
from pathlib import Path

import yaml
from sqlalchemy import delete, select

from app.db.models import FAQ, Store
from app.db.session import SessionLocal


def main():
    parser = argparse.ArgumentParser(description="Загрузка FAQ магазина из YAML")
    parser.add_argument("--store", required=True)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    data = yaml.safe_load(Path(args.file).read_text(encoding="utf-8"))
    if data.get("demo"):
        print("⚠️  ДЕМО-FAQ: ответы не настоящие, замени их перед реальным запуском")

    with SessionLocal() as db:
        store = db.scalar(select(Store).where(Store.name == args.store))
        if store is None:
            raise SystemExit(f"Магазин {args.store!r} не найден")

        db.execute(delete(FAQ).where(FAQ.store_id == store.id))  # заменяем FAQ магазина целиком

        count, skipped = 0, 0
        for item in data["items"]:
            for lang in ("ru", "az"):
                entry = item.get(lang)
                answer = (entry or {}).get("a") or ""
                if not answer.strip() or "TODO" in answer:
                    skipped += 1
                    continue
                db.add(FAQ(
                    store_id=store.id,
                    question=entry["q"].strip(),
                    answer=answer.strip(),
                    lang=lang,
                    category=item["category"],
                ))
                count += 1

        db.commit()
        print(f"FAQ загружено: {count}, пропущено незаполненных: {skipped}")


if __name__ == "__main__":
    main()