from app.db.models import Product

GENDER_LABELS = {
    "female": "женский аромат, qadın ətri",
    "male": "мужской аромат, kişi ətri",
    "unisex": "унисекс, uniseks ətir",
}
CONC_LABELS = {
    "EDP": "парфюмерная вода (Eau de Parfum)",
    "EDT": "туалетная вода (Eau de Toilette)",
    "EDC": "одеколон (Eau de Cologne)",
    "Parfum": "духи (Parfum)",
}


def product_text(p: Product) -> str:
    attrs = p.attributes or {}
    parts = [
        p.title,
        f"Бренд: {p.brand}" if p.brand else None,
        GENDER_LABELS.get(attrs.get("gender")),
        CONC_LABELS.get(attrs.get("concentration")),
        (p.description or "")[:1500],
    ]
    return "\n".join(x for x in parts if x)