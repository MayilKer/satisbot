import argparse
import readline
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import select

from app.agent.builder import get_graph
from app.db.models import Store
from app.db.session import SessionLocal


def text_of(message) -> str:
    """У Claude content бывает строкой или списком блоков — достаём текст."""
    if isinstance(message.content, str):
        return message.content
    return "".join(b.get("text", "") for b in message.content if isinstance(b, dict))

def clean(text: str) -> str:
    """Убирает «осколки» байтов, которые терминал мог оставить при редактировании строки."""
    return text.encode("utf-8", "surrogateescape").decode("utf-8", "ignore").strip()

def tools_used_this_turn(messages) -> list[str]:
    names = []
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            break
        if isinstance(m, AIMessage) and m.tool_calls:
            names.extend(c["name"] for c in m.tool_calls)
    return list(reversed(names))


def main():
    parser = argparse.ArgumentParser(description="Чат с SatışBot в терминале")
    parser.add_argument("--store", required=True)
    parser.add_argument("--thread", default="cli:test1", help="id диалога: один thread — одна история")
    args = parser.parse_args()

    with SessionLocal() as db:
        store = db.scalar(select(Store).where(Store.name == args.store))
    graph = get_graph()
    config = {
        "configurable": {"thread_id": f"{store.id}:{args.thread}"},
        "run_name": "chat_turn",
        "metadata": {"store_id": store.id, "channel": "cli"},
        "recursion_limit": 25,  # страховка от бесконечного цикла agent ⇄ tools
    }

    print("Пиши сообщение (пустая строка или exit — выход)")
    while True:
        text = clean(input("\n👤 "))
        if text in ("", "exit", "quit"):
            break
        result = graph.invoke({"messages": [HumanMessage(content=text)], "store_id": store.id}, config=config)
        print(f"   [{result['language']} | {result['intent']} | фильтры: {result.get('filters')} "
              f"| tools: {tools_used_this_turn(result['messages'])}]")
        print(f"🤖 {text_of(result['messages'][-1])}")


if __name__ == "__main__":
    main()