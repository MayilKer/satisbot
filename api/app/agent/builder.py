from functools import lru_cache

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from psycopg_pool import ConnectionPool

from app.agent.nodes import (agent_node, handoff_node, route_after_agent,
                             route_after_understand, tools_node, understand_node)
from app.agent.state import ChatState
from app.config import settings


def build_graph(checkpointer):
    g = StateGraph(ChatState)
    g.add_node("understand", understand_node)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)
    g.add_node("handoff", handoff_node)

    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", route_after_understand, {"agent": "agent", "handoff": "handoff"})
    g.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "end": END})
    g.add_edge("tools", "agent")  # цикл ReAct: после tools агент думает снова
    g.add_edge("handoff", END)
    return g.compile(checkpointer=checkpointer)


@lru_cache
def get_graph():
    # psycopg (v3) понимает обычный postgresql://, а не формат SQLAlchemy postgresql+psycopg2://
    conninfo = settings.database_url.replace("postgresql+psycopg2://", "postgresql://")
    pool = ConnectionPool(conninfo=conninfo, max_size=10, open=True,
                          kwargs={"autocommit": True, "prepare_threshold": 0})
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()  # создаёт таблицы чекпоинтов, если их ещё нет
    return build_graph(checkpointer)