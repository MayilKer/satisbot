from typing import Literal

from pydantic import BaseModel


class SearchFilters(BaseModel):
    gender: Literal["female", "male", "unisex"] | None = None
    include_unisex: bool = True  # «женский» → показываем и унисекс
    concentration: Literal["EDP", "EDT", "EDC", "Parfum"] | None = None
    min_price: float | None = None
    max_price: float | None = None
    in_stock_only: bool = True


class ProductHit(BaseModel):
    product_id: int
    title: str
    brand: str | None
    price_azn: float | None
    old_price_azn: float | None
    price_is_demo: bool
    in_stock: bool
    gender: str | None
    concentration: str | None
    image_url: str | None
    score: float