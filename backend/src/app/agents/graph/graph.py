from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents.graph.nodes import (
    classify_user_intent,
    compose_decision_context,
    generate_chat_response,
    generate_greeting_response,
    generate_unsupported_response,
    run_restaurant_tools,
    select_tools_for_intent,
)
from app.agents.graph.state import ChatGraphState


@lru_cache(maxsize=1)
def get_chat_graph():
    graph_builder = StateGraph(ChatGraphState)
    graph_builder.add_node("classify_user_intent", classify_user_intent)
    graph_builder.add_node("select_tools_for_intent", select_tools_for_intent)
    graph_builder.add_node("run_restaurant_tools", run_restaurant_tools)
    graph_builder.add_node("compose_decision_context", compose_decision_context)
    graph_builder.add_node("generate_chat_response", generate_chat_response)
    graph_builder.add_node("generate_greeting_response", generate_greeting_response)
    graph_builder.add_node("generate_unsupported_response", generate_unsupported_response)
    graph_builder.add_edge(START, "classify_user_intent")
    graph_builder.add_conditional_edges(
        "classify_user_intent",
        route_after_intent_classification,
        {
            "greeting": "generate_greeting_response",
            "unsupported": "generate_unsupported_response",
            "chat": "select_tools_for_intent",
        },
    )
    graph_builder.add_edge("select_tools_for_intent", "run_restaurant_tools")
    graph_builder.add_edge("run_restaurant_tools", "compose_decision_context")
    graph_builder.add_edge("compose_decision_context", "generate_chat_response")
    graph_builder.add_edge("generate_chat_response", END)
    graph_builder.add_edge("generate_greeting_response", END)
    graph_builder.add_edge("generate_unsupported_response", END)
    return graph_builder.compile()


def route_after_intent_classification(state: ChatGraphState) -> str:
    if state["intent_category"] == "greeting":
        return "greeting"
    if state["intent_category"] == "unknown":
        return "unsupported"
    return "chat"


def reset_chat_graph() -> None:
    get_chat_graph.cache_clear()
