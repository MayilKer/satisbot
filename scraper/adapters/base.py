from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterator


@dataclass
class ProductData:
    """Единый формат товара — одинаковый для любого источника."""
    external_id: str
    title: str
    source_url: str | None = None
    price_azn: Decimal | None = None
    old_price_azn: Decimal | None = None
    in_stock: bool = True
    brand: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)
    description: str | None = None
    image_urls: list[str] = field(default_factory=list)
    attributes: dict = field(default_factory=dict)


class CatalogAdapter(ABC):
    @abstractmethod
    def fetch_products(self) -> Iterator[ProductData]:
        """Отдаёт товары по одному (генератор), чтобы не держать весь каталог в памяти."""
