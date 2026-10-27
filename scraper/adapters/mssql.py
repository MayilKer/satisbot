import os
import re
from decimal import Decimal
from typing import Iterator

from sqlalchemy import create_engine, text

from scraper.adapters.base import CatalogAdapter, ProductData

PRODUCTS_SQL = text("""
    SELECT p.Id, p.Name, p.Description, p.Price, p.IsAvailable, b.Name AS Brand
    FROM dbo.Products p
    JOIN dbo.Brands b ON b.Id = p.BrandId
    ORDER BY p.Id
""")

# TODO: подставь реальные имена колонок из проверки в пункте 0
IMAGES_SQL = text("SELECT ProductId, ImageUrl FROM dbo.ProductImages ORDER BY ProductId, Id")

CONCENTRATION = [
    ("парфюмерная вода", "EDP"),
    ("туалетная вода", "EDT"),
    ("одеколон", "EDC"),
]
YEAR_RE = re.compile(r"в (\d{4}) году")
SPACES_RE = re.compile(r"[ \t]+")


def clean(value: str | None) -> str | None:
    if not value:
        return None
    value = SPACES_RE.sub(" ", value).strip()
    return value or None


class MssqlAdapter(CatalogAdapter):
    def __init__(self, env_var: str):
        url = os.environ.get(env_var)
        if not url:
            raise RuntimeError(f"Переменная окружения {env_var} не задана в .env")
        self.engine = create_engine(url)

    def fetch_products(self) -> Iterator[ProductData]:
        with self.engine.connect() as conn:
            images = self._load_images(conn)
            for row in conn.execute(PRODUCTS_SQL).mappings():
                yield self._parse(row, images.get(row["Id"], []))

    def _load_images(self, conn) -> dict[int, list[str]]:
        images: dict[int, list[str]] = {}
        for r in conn.execute(IMAGES_SQL).mappings():
            images.setdefault(r["ProductId"], []).append(r["ImageUrl"])
        return images

    def _parse(self, row, image_urls: list[str]) -> ProductData:
        description = clean(row["Description"])
        return ProductData(
            external_id=str(row["Id"]),
            title=clean(row["Name"]),
            price_azn=Decimal(row["Price"]) if row["Price"] is not None else None,
            in_stock=bool(row["IsAvailable"]),
            brand=clean(row["Brand"]),
            description=description,
            image_urls=image_urls,
            attributes=self._attributes(row["Name"], description or ""),
        )

    @staticmethod
    def _attributes(name: str, description: str) -> dict:
        text_lower = f"{name} {description}".lower()
        attrs: dict = {}
        # TODO: concentration — первое совпадение из CONCENTRATION, которое встречается в text_lower
        for phrase, code in CONCENTRATION:
            if phrase in text_lower:
                attrs["concentration"] = code
                break

        unisex = ("унисекс", "для женщин и мужчин", "для мужчин и женщин")
        if any(phrase in text_lower for phrase in unisex):
            attrs["gender"] = "unisex"
        elif "для женщин" in text_lower:
            attrs["gender"] = "female"
        elif "для мужчин" in text_lower:
            attrs["gender"] = "male"

        # TODO: release_year — YEAR_RE.search(description) → int(match.group(1))
        match = YEAR_RE.search(description)
        if match:
            attrs["release_year"] = int(match.group(1))
        return attrs