import numpy as np
from redis.commands.search import result
from sqlalchemy import select

from app.db.models import Product
from app.db.session import SessionLocal
from app.services.embeddings import embed_documents, embed_query

MODELS = ["voyage-4-lite", "voyage-4"]
SAMPLE = 150
QUERIES = [
    "qadın üçün şirin ətir",                    # сладкий аромат для женщин
    "kişilər üçün təravətli sitrus ətri",       # свежий цитрусовый для мужчин
    "odunsu uniseks ətir",                      # древесный унисекс
    "gündəlik istifadə üçün yüngül çiçəkli ətir",  # лёгкий цветочный на каждый день
    "сладкий аромат для женщин",                # тот же смысл по-русски — для сравнения
]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))



def doc_text(p: Product) -> str:
    attrs = p.attributes or {}
    parts = [p.title, p.brand, attrs.get("gender"), attrs.get("concentration"), (p.description or "")[:800]]
    return " | ".join(str(x) for x in parts if x)


def main():
    with SessionLocal() as db:
        products = db.scalars(select(Product).order_by(Product.id).limit(SAMPLE)).all()
    texts = [doc_text(p) for p in products]

    for model in MODELS:
        print(f"\n===== {model} =====")
        doc_vecs = np.array(embed_documents(texts, model=model))
        for q in QUERIES:
            q_vec = np.array(embed_query(q, model=model))
            scores = [cosine(q_vec, d) for d in doc_vecs]
            top = np.argsort(scores)[::-1][:3]
            print(f"\n🔎 {q}")
            for i in top:
                gender = (products[i].attributes or {}).get("gender", "?")
                print(f"   {scores[i]:.3f}  {products[i].title}  [{gender}]")


if __name__ == "__main__":
    main()