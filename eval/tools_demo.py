import json

from sqlalchemy import select

from app.agent.tools import build_tools
from app.agent.understand import llm
from app.db.models import Store
from app.db.session import SessionLocal


def show(title, value):
    print(f"\n=== {title} ===")
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str)[:1500])


def main():
    with SessionLocal() as db:
        store = db.scalar(select(Store).where(Store.name == "Marthouse"))
    tools = build_tools(store.id)
    search, get_product, faq = tools

    # 1. Что видит модель: имя, описание, схема аргументов
    for t in tools:
        print(f"\n🔧 {t.name}: {t.description.splitlines()[0]}\n   аргументы: {list(t.args)}")

    # 2. Прямые вызовы без LLM
    found = search.invoke({"query_ru": "сладкий аромат", "gender": "female", "max_price": 150})
    show("search_products", found)
    if isinstance(found, list):
        show("get_product (свой товар)", get_product.invoke({"product_id": found[0]["product_id"]}))
    show("get_product (несуществующий)", get_product.invoke({"product_id": 999999}))
    show("faq_lookup", faq.invoke({"question": "Bakıya çatdırılma nə qədərdir?"}))

    # 3. Какой tool выбирает Claude (только выбор, без выполнения)
    llm_with_tools = llm.bind_tools(tools)
    for msg in ["150 manata qədər qadın üçün şirin ətir",
                "Bakıya çatdırılma nə qədərdir?",
                "Ətirləriniz orijinaldır?"]:
        response = llm_with_tools.invoke(msg)
        calls = [(c["name"], c["args"]) for c in response.tool_calls]
        print(f"\n💬 «{msg}»\n   → {calls}")


if __name__ == "__main__":
    main()