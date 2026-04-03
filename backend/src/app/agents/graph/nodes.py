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


def generate_unsupported_response(_: ChatGraphState) -> ChatGraphState:
    return {
        "messages": [
            AIMessage(
                content=(
                    "Sorry, I can only help with a fixed set of restaurant questions right now. "
                    "Try one of these examples:\n"
                    "- Is this restaurant worth it?\n"
                    "- Should I go or skip?\n"
                    "- How is the food?\n"
                    "- How is the service?\n"
                    "- Is it expensive?\n"
                    "- How is the ambience?\n"
                    "- Is it good for a date?\n"
                    "- Is it family friendly?\n"
                    "- Is it good for a quick meal?\n"
                    "- Any common complaints?\n"
                    "- Any warnings?\n"
                    "- Give me a summary."
                )
            )
        ]
    }


def generate_chat_response(state: ChatGraphState) -> ChatGraphState:
    model = get_chat_model()
    response = model.invoke(state["messages"])
    if not isinstance(response, AIMessage):
        response = AIMessage(content=str(response.content))
    return {"messages": [response]}
