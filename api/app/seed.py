from sqlalchemy import select

from app.db.models import Store
from app.db.session import Base, SessionLocal, engine

DARAQ = {
    "name": "Daraq Store",
    "source_type": "shopify",
    "source_url": "https://daraq.store",
    "attribute_schema": {
        "volume_ml": {"type": "number", "label_az": "həcm (ml)", "label_ru": "объём (мл)"},
    },
    "languages": ["az", "ru"],
}


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(Store).where(Store.name == DARAQ["name"])):
            db.add(Store(**DARAQ))
            db.commit()
            print("Store created")
        else:
            print("Store already exists")


if __name__ == "__main__":
    main()