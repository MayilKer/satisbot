import re
import time
from decimal import Decimal
from typing import Iterator

import httpx
from bs4 import BeautifulSoup

from scraper.adapters.base import CatalogAdapter, ProductData

USER_AGENT = "SatisBot-StudentProject/0.1 (+https://github.com/MayilKer/satisbot)"
VOLUME_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*ml\b", re.IGNORECASE)
JUNK_RE = re.compile(r":chatgpt-content-reference\{[^}]*\}|```\w*")


class ShopifyAdapter(CatalogAdapter):
    def __init__(self, base_url: str, delay_sec: float = 2.0, page_size: int = 100, max_retries: int = 5):
        self.base_url = base_url.rstrip("/")
        self.delay_sec = delay_sec
        self.page_size = page_size
        self.max_retries = max_retries

    def fetch_products(self) -> Iterator[ProductData]:
        page = 1
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as client:
            while True:
                products = self._get_page(client, page)
                if not products:
                    break
                for raw in products:
                    yield self._parse(raw)
                print(f"Страница {page}: {len(products)} товаров")
                page += 1
                time.sleep(self.delay_sec)  # вежливая пауза для сайта

    def _get_page(self, client: httpx.Client, page: int) -> list[dict]:
        for attempt in range(1, self.max_retries + 1):
            resp = client.get(
                f"{self.base_url}/products.json",
                params={"limit": self.page_size, "page": page},
            )
            if resp.status_code == 429:
                try:
                    wait = float(resp.headers.get("Retry-After", ""))
                except ValueError:
                    wait = 5 * 2 ** attempt  # 10, 20, 40, 80… секунд
                print(f"429 на странице {page}: жду {wait:.0f} с (попытка {attempt}/{self.max_retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["products"]
        raise RuntimeError(f"Страница {page}: сайт отвечает 429 после {self.max_retries} попыток")

    def _parse(self, raw: dict) -> ProductData:
        variants = raw.get("variants") or [{}]
        first = variants[0]

        price = Decimal(first["price"])
        compare = first.get("compare_at_price")
        old_price = Decimal(compare) if compare and Decimal(compare) > price else None
        in_stock = any(v.get("available") for v in variants)

        return ProductData(
            external_id=str(raw["id"]),
            source_url=f"{self.base_url}/products/{raw['handle']}",
            title=raw["title"].strip(),
            price_azn=price,
            old_price_azn=old_price,
            in_stock=in_stock,
            brand=raw.get("vendor") or None,
            category=raw.get("product_type") or None,
            tags=raw.get("tags") or [],
            description=self._clean_html(raw.get("body_html")),
            image_urls=[img["src"] for img in raw.get("images", [])],
            attributes=self._attributes(raw),
        )

    @staticmethod
    def _clean_html(html: str | None) -> str | None:
        if not html:
            return None
        text = BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)
        text = JUNK_RE.sub("", text).strip()
        return text or None

    @staticmethod
    def _attributes(raw: dict) -> dict:
        attrs: dict = {}
        # Опции Shopify (Size, Color…) → атрибуты; "Title" — заглушка для товаров без вариантов
        for opt in raw.get("options", []):
            if opt["name"].lower() != "title":
                attrs[opt["name"].lower()] = opt["values"]
        match = VOLUME_RE.search(raw["title"])
        if match:
            attrs["volume_ml"] = float(match.group(1).replace(",", "."))
        return attrs
