from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.db.models import Product
from app.db.session import SessionLocal
from app.schemas.search import SearchFilters
from app.services.faq import search_faq
from app.services.search import search_products


class SearchProductsInput(BaseModel):
    query_ru: str = Field(description="Что ищет покупатель, на русском: характер аромата, ноты, повод, бренд. Без цены и пола — они идут в фильтры")
    gender: Literal["female", "male", "unisex"] | None = Field(None, description="Для кого аромат, если покупатель сказал явно")
    concentration: Literal["EDP", "EDT", "EDC", "Parfum"] | None = Field(None, description="Концентрация, если покупатель назвал явно")
    min_price: float | None = Field(None, description="Минимальная цена в AZN")
    max_price: float | None = Field(None, description="Максимальная цена в AZN")


class GetProductInput(BaseModel):
    product_id: int = Field(description="id товара из результатов search_products")


class FaqLookupInput(BaseModel):
    question: str = Field(description="Вопрос покупателя о доставке, оплате, возврате, оригинальности, режиме работы и т.п.")


def build_tools(store_id: int) -> list:
    """Фабрика: tools «привязаны» к магазину. store_id модель не видит и подменить не может."""

    @tool("search_products", args_schema=SearchProductsInput)
    def search_products_tool(query_ru: str, gender=None, concentration=None,
                             min_price=None, max_price=None) -> list | dict:
        """Ищет духи в каталоге магазина по описанию и фильтрам. Возвращает до 5 товаров с актуальной ценой и наличием.
        Используй, когда покупатель ищет аромат или уточняет поиск."""
        try:
            filters = SearchFilters(gender=gender, concentration=concentration,
                                    min_price=min_price, max_price=max_price)
            with SessionLocal() as db:
                hits = search_products(db, store_id, query_ru, filters)
            if not hits:
                return {"result": "Ничего не найдено. Предложи покупателю смягчить условия: цену, пол или описание."}
            return [h.model_dump(exclude={"score"}) for h in hits]
        except Exception as e:
            return {"error": f"Поиск временно недоступен ({type(e).__name__}). Извинись и предложи позвать менеджера."}

    @tool("get_product", args_schema=GetProductInput)
    def get_product_tool(product_id: int) -> dict:
        """Подробности о товаре: описание, ноты, цена, старая цена, наличие.
        Используй перед тем, как называть цену или отвечать на детальный вопрос о конкретном аромате."""
        with SessionLocal() as db:
            p = db.get(Product, product_id)
            if p is None or p.store_id != store_id:
                return {"error": f"Товар {product_id} не найден в этом магазине"}
            else:
                attrs = p.attributes or {}
                return {
                    "product_id": p.id,
                    "title": p.title,
                    "brand": p.brand,
                    "price_azn": float(p.price_azn) if p.price_azn is not None else None,
                    "old_price_azn": float(p.old_price_azn) if p.old_price_azn is not None else None,
                    "price_is_demo": bool(attrs.get("price_is_demo")),
                    "in_stock": p.in_stock,
                    "attributes": attrs,
                    "description": (p.description or "")[:1000],
                    "image_urls": (p.image_urls or [])[:3],
                }
    @tool("faq_lookup", args_schema=FaqLookupInput)
    def faq_lookup_tool(question: str) -> list | dict:
        """Ищет ответ в FAQ магазина: доставка, оплата, рассрочка, возврат, оригинальность, тестеры, упаковка, контакты, самовывоз.
        Отвечай покупателю только на основе найденного; если ответа нет — предложи менеджера."""
        try:
            return search_faq(store_id, question)
        except Exception as e:
            return {"error": f"FAQ временно недоступен ({type(e).__name__})"}

    return [search_products_tool, get_product_tool, faq_lookup_tool]