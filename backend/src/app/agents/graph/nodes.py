from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.graph.state import ChatGraphState
from app.core.llm import get_chat_model


def generate_chat_response(state: ChatGraphState) -> ChatGraphState:
    model = get_chat_model()
    response = model.invoke(state["messages"])
    if not isinstance(response, AIMessage):
        response = AIMessage(content=str(response.content))
    return {"messages": [response]}
