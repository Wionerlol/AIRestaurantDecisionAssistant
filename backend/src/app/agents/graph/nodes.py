from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.graph.state import ChatGraphState
from app.core.llm import get_chat_model
from app.services.intent_service import classify_intent


def classify_user_intent(state: ChatGraphState) -> ChatGraphState:
    latest_user_message = next(
        (message.content for message in reversed(state["messages"]) if message.type == "human"),
        "",
    )
    intent = classify_intent(latest_user_message)
    return {
        "intent_category": intent.category,
        "intent_label": intent.label,
    }


def generate_chat_response(state: ChatGraphState) -> ChatGraphState:
    model = get_chat_model()
    response = model.invoke(state["messages"])
    if not isinstance(response, AIMessage):
        response = AIMessage(content=str(response.content))
    return {"messages": [response]}
