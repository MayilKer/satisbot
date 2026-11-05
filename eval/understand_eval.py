from langchain_core.messages import HumanMessage
from sqlalchemy import select

from app.agent.understand import build_understand_chain
from app.db.models import Store
from app.db.session import SessionLocal

# сообщение → ожидаемые поля (проверяем только указанные)
CASES = [
    ("150 manata qədər qadın üçün şirin ətir", {"language": "az", "intent": "product", "gender": "female", "max_price": 150}),
    ("есть что-нибудь мужское древесное до 200 манат?", {"language": "ru", "intent": "product", "gender": "male", "max_price": 200}),
    ("Bakıya çatdırılma nə qədərdir?", {"language": "az", "intent": "faq"}),
    ("Хочу скидку 20 процентов", {"language": "ru", "intent": "handoff"}),
    ("salam", {"intent": "smalltalk"}),
    ("salam, есть парфюмерная вода для женщин?", {"language": "mixed", "intent": "product", "gender": "female", "concentration": "EDP"}),
    ("Lattafa Yara Moi almaq istəyirəm, necə sifariş edim?", {"language": "az", "intent": "order"}),
    ("Do you have unisex oud perfumes?", {"language": "en", "intent": "product", "gender": "unisex"}),
    ("operatorla danışmaq istəyirəm", {"language": "az", "intent": "handoff"}),
]


def flatten(u) -> dict:
    """Understanding → плоский словарь, чтобы сравнивать с ожиданиями."""
    return {"language": u.language, "intent": u.intent, "query_ru": u.search_query_ru, **u.filters.model_dump()}


def main():
    with SessionLocal() as db:
        store = db.scalar(select(Store).where(Store.name == "Marthouse"))
    chain = build_understand_chain(store.attribute_schema)

    passed = 0
    for text, expected in CASES:
        actual = flatten(chain.invoke({"messages": [HumanMessage(content=text)]}))
        errors = [field for field, value in expected.items() if actual.get(field) != value]
        if not errors:
            passed += 1
        mark = "✅" if not errors else f"❌ {errors}"
        print(f"{mark}  «{text}»\n     → {actual}")
    print(f"\nПройдено: {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()