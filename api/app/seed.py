from sqlalchemy import select

from app.db.models import Store
from app.db.session import Base, SessionLocal, engine

MARTHOUSE = {
    "name": "Marthouse",
    "source_type": "mssql",
    "source_url": "MARTHOUSE_DB_URL",  # имя переменной окружения, пароль — только в .env
    "attribute_schema": {
        "concentration": {"type": "enum", "values": ["EDP", "EDT", "EDC"], "label_ru": "концентрация"},
        "gender": {"type": "enum", "values": ["female", "male", "unisex"], "label_ru": "для кого"},
        "release_year": {"type": "number", "label_ru": "год выпуска"},
    },
    "languages": ["az", "ru"],
}


def main():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(Store).where(Store.name == MARTHOUSE["name"])):
            db.add(Store(**MARTHOUSE))
            db.commit()
            print("Store created")
        else:
            print("Store already exists")


if __name__ == "__main__":
    main()