from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ChatState(TypedDict, total=False):  # total=False: на вход хватает messages и store_id
    messages: Annotated[list[AnyMessage], add_messages]  # reducer: новые сообщения ДОПИСЫВАЮТСЯ
    store_id: int
    language: str
    intent: str
    search_query_ru: str | None
    filters: dict
    handoff_reason: str | None
    steps: int  # сколько раз за этот ход вызывались tools