from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.graph.nodes import classify_user_intent, generate_chat_response
from app.agents.graph.state import ChatGraphState


@lru_cache(maxsize=1)
def get_chat_graph():
    graph_builder = StateGraph(ChatGraphState)
    graph_builder.add_node("classify_user_intent", classify_user_intent)
    graph_builder.add_node("generate_chat_response", generate_chat_response)
    graph_builder.add_edge(START, "classify_user_intent")
    graph_builder.add_edge("classify_user_intent", "generate_chat_response")
    graph_builder.add_edge("generate_chat_response", END)
    return graph_builder.compile()


def reset_chat_graph() -> None:
    get_chat_graph.cache_clear()
