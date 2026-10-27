from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    source_type: Mapped[str] = mapped_column(String(20))  # shopify / html / csv
    source_url: Mapped[str] = mapped_column(String(500))
    attribute_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    languages: Mapped[list] = mapped_column(JSONB, default=lambda: ["az", "ru"])
    operator_chat_id: Mapped[str | None] = mapped_column(String(50))
    tone: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    products: Mapped[list["Product"]] = relationship(back_populates="store")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("store_id", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    external_id: Mapped[str] = mapped_column(String(100))  # id товара в магазине (Shopify product id)
    source_url: Mapped[str | None] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500))
    category: Mapped[str | None] = mapped_column(String(200), index=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    brand: Mapped[str | None] = mapped_column(String(200), index=True)
    price_azn: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    old_price_azn: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_urls: Mapped[list] = mapped_column(JSONB, default=list)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict)
    # TODO: brand — String(200), может быть None, с index=True
    # TODO: price_azn — Mapped[Decimal], Numeric(10, 2)
    # TODO: old_price_azn — как price_azn, но может быть None
    # TODO: in_stock — Boolean, default=True
    # TODO: description — Text, может быть None
    # TODO: image_urls — JSONB, default=list
    # TODO: attributes — JSONB, default=dict
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    store: Mapped["Store"] = relationship(back_populates="products")


class FAQ(Base):
    __tablename__ = "faq"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(5))
    category: Mapped[str | None] = mapped_column(String(100))