import json
from pathlib import Path
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field

from app.config import settings

PROMPT_VERSION = "understand_v2"
PROMPTS_DIR = Path(__file__).parent / "prompts"


class ExtractedFilters(BaseModel):
    gender: Literal["female", "male", "unisex"] | None = None
    concentration: Literal["EDP", "EDT", "EDC", "Parfum"] | None = None
    min_price: float | None = None
    max_price: float | None = None


class Understanding(BaseModel):
    language: Literal["az", "ru", "en", "mixed"] = Field(description="Язык последнего сообщения покупателя")
    intent: Literal["product", "faq", "order", "handoff", "smalltalk"] = Field(description="Намерение покупателя")
    search_query_ru: str | None = Field(default=None, description="Поисковый запрос на русском без фильтров; только для intent=product")
    filters: ExtractedFilters = Field(default_factory=ExtractedFilters, description="Фильтры, названные покупателем явно")
    handoff_reason: str | None = Field(default=None, description="Почему нужен оператор; только для intent=handoff")


llm = ChatAnthropic(model=settings.llm_model, api_key=settings.anthropic_api_key)


def build_understand_chain(attribute_schema: dict):
    system = (PROMPTS_DIR / f"{PROMPT_VERSION}.md").read_text(encoding="utf-8")
    prompt = ChatPromptTemplate.from_messages([
        ("system", system),
        MessagesPlaceholder("messages"),  # история диалога + последнее сообщение
    ]).partial(attribute_schema=json.dumps(attribute_schema, ensure_ascii=False))

    chain = prompt | llm.with_structured_output(Understanding)  # LCEL
    return chain.with_config(run_name="understand", metadata={"prompt_version": PROMPT_VERSION})