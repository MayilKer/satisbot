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
IMAGES_SQL = text("SELECT ProductId, ImageUrl FROM dbo.ProductImages ORDER BY ProductId, Id")

CONCENTRATION_RULES = [
    # порядок важен: "eau de parfum" содержит "parfum", поэтому EDP проверяем раньше Parfum
    (re.compile(r"eau de parfum|\bedp\b|парфюмерная вода|парфюмированная вода"), "EDP"),
    (re.compile(r"eau de toilette|\bedt\b|туалетная вода"), "EDT"),
    (re.compile(r"eau de cologne|\bedc\b|одеколон"), "EDC"),
    (re.compile(r"\bextrait\b|\ble parfum\b|\bparfum\b|экстракт духов"), "Parfum"),
]
UNISEX_RE = re.compile(r"унисекс|для (?:мужчин и женщин|женщин и мужчин)|для него и для не[её]|\bunisex\b")
FEMALE_RE = re.compile(r"женск|дамск|для женщин|для не[её]\b|\bfor her\b|\bpour femme\b|\bwoman\b|\bher\b")
MALE_RE = re.compile(r"мужск|для мужчин|для него\b|джентльмен|\bfor him\b|\bpour homme\b|\bman\b|\bhim\b|\bgentleman\b")
YEAR_RE = re.compile(r"в (\d{4}) году")
SPACES_RE = re.compile(r"[ \t]+")


def clean(value: str | None) -> str | None:
    if not value:
        return None
    value = SPACES_RE.sub(" ", value).strip()
    return value or None


def detect_concentration(title: str, description: str) -> str | None:
    for txt in (title.lower(), description.lower()):  # название надёжнее описания
        for pattern, code in CONCENTRATION_RULES:
            if pattern.search(txt):
                return code
    return None


def detect_gender(title: str, description: str) -> str | None:
    for txt in (title.lower(), description.lower()):  # сначала название, потом описание
        if UNISEX_RE.search(txt):
            return "unisex"
        female, male = FEMALE_RE.search(txt), MALE_RE.search(txt)
        if female and male:
            # упомянуты оба — побеждает то, что встречается раньше
            return "female" if female.start() < male.start() else "male"
        if female:
            return "female"
        if male:
            return "male"
    return None


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
        attrs: dict = {}
        concentration = detect_concentration(name, description)
        if concentration:
            attrs["concentration"] = concentration
        gender = detect_gender(name, description)
        if gender:
            attrs["gender"] = gender
        match = YEAR_RE.search(description)
        if match:
            attrs["release_year"] = int(match.group(1))
        return attrs