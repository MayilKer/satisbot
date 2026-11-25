import json
from functools import lru_cache
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, trim_messages

from app.agent.state import ChatState
from app.agent.tools import build_tools
from app.agent.understand import build_understand_chain, llm
from app.db.models import Store
from app.db.session import SessionLocal

AGENT_PROMPT_VERSION = "agent_v1"
AGENT_PROMPT = (Path(__file__).parent / "prompts" / f"{AGENT_PROMPT_VERSION}.md").read_text(encoding="utf-8")
MAX_TOOL_STEPS = 5
HISTORY_WINDOW = 20  # сколько последних сообщений видит агент

HANDOFF_TEXT = {
    "az": "Sorğunuzu menecerə ötürürəm, tezliklə sizinlə əlaqə saxlayacaq.",
    "ru": "Передаю ваш вопрос менеджеру, он скоро свяжется с вами.",
    "en": "I'm passing your request to a manager, they will contact you shortly.",
}


@lru_cache
def understand_chain_for(store_id: int):
    """Одна цепочка understand на магазин: схема фильтров берётся из настроек магазина."""
    with SessionLocal() as db:
        store = db.get(Store, store_id)
        return build_understand_chain(store.attribute_schema)


def conversation_only(messages: list) -> list:
    """Для understand нужен только «разговор»: реплики покупателя и текстовые ответы бота, без вызовов tools."""
    history = [m if isinstance(m, HumanMessage) else text_only(m)
               for m in messages
               if isinstance(m, HumanMessage) or (isinstance(m, AIMessage) and not m.tool_calls)]
    history = history[-10:]
    while history and not isinstance(history[0], HumanMessage):  # диалог должен начинаться с покупателя
        history.pop(0)
    return history

def strip_thinking(message):
    """Убирает подписанные блоки thinking из ответа модели: остаются текст и вызовы tools."""
    if isinstance(message, AIMessage) and isinstance(message.content, list):
        blocks = [b for b in message.content
                  if not (isinstance(b, dict) and b.get("type") in ("thinking", "redacted_thinking"))]
        return message.model_copy(update={"content": blocks})
    return message


def text_only(message) -> AIMessage:
    """Ответ бота как обычный текст — для understand, которому нужен только смысл разговора."""
    if isinstance(message.content, str):
        return AIMessage(content=message.content)
    text = "".join(b.get("text", "") for b in message.content if isinstance(b, dict))
    return AIMessage(content=text)

# ---------- узлы ----------

def understand_node(state: ChatState) -> dict:
    u = understand_chain_for(state["store_id"]).invoke({"messages": conversation_only(state["messages"])})
    return {
        "language": u.language,
        "intent": u.intent,
        "search_query_ru": u.search_query_ru,
        "filters": u.filters.model_dump(exclude_none=True),
        "handoff_reason": u.handoff_reason,
        "steps": 0,  # новый ход — счётчик вызовов tools с нуля
    }


def agent_node(state: ChatState) -> dict:
    hint = (f"intent: {state['intent']}; поисковый запрос на русском: {state.get('search_query_ru')}; "
            f"фильтры: {state.get('filters')}")
    system = SystemMessage(AGENT_PROMPT.replace("{language}", state["language"]).replace("{hint}", hint))
    # последние сообщения; start_on="human" не даёт окну начаться с «обрезанного» вызова tool
    window = trim_messages(state["messages"], strategy="last", token_counter=len,
                           max_tokens=HISTORY_WINDOW, start_on="human")
    last_human = max(i for i, m in enumerate(window) if isinstance(m, HumanMessage))
    window = [strip_thinking(m) if i < last_human else m for i, m in enumerate(window)]
    response = llm.bind_tools(build_tools(state["store_id"])).invoke(
        [system, *window],
        config={"run_name": "agent", "metadata": {"prompt_version": AGENT_PROMPT_VERSION}},
    )
    return {"messages": [response]}


def tools_node(state: ChatState) -> dict:
    """Выполняет все вызовы tools из последнего ответа агента. На КАЖДЫЙ вызов — свой ToolMessage."""
    tools = {t.name: t for t in build_tools(state["store_id"])}
    steps = state.get("steps", 0) + 1
    results = []
    for call in state["messages"][-1].tool_calls:
        if steps > MAX_TOOL_STEPS:
            output = {"error": "Лимит вызовов инструментов исчерпан. Ответь покупателю на основе уже найденного."}
        elif call["name"] not in tools:
            output = {"error": f"Неизвестный инструмент {call['name']}"}
        else:
            output = tools[call["name"]].invoke(call["args"])
        results.append(ToolMessage(
            content=json.dumps(output, ensure_ascii=False, default=str),
            tool_call_id=call["id"],
            name=call["name"],
        ))
    return {"messages": results, "steps": steps}


def handoff_node(state: ChatState) -> dict:
    # заглушка: на Дне 4 здесь будет interrupt() и панель оператора
    text = HANDOFF_TEXT.get(state.get("language"), HANDOFF_TEXT["az"])
    return {"messages": [AIMessage(content=text)]}


# ---------- маршруты (условные рёбра) ----------

def route_after_understand(state: ChatState) -> str:
    if state["intent"] == "handoff":
        return "handoff"
    return "agent"


def route_after_agent(state: ChatState) -> str:
    if state["messages"][-1].tool_calls:
        return "tools"
    return "end"