from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.graph.graph import get_chat_graph
from app.core.config import settings
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse


ROLE_TO_MESSAGE = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


def run_chat(request: ChatRequest) -> ChatResponse:
    messages = []
    if settings.chat_system_prompt:
        messages.append(SystemMessage(content=settings.chat_system_prompt))

    for message in request.messages:
        message_cls = ROLE_TO_MESSAGE[message.role]
        messages.append(message_cls(content=message.content))

    result = get_chat_graph().invoke({"messages": messages})
    final_message = result["messages"][-1]

    return ChatResponse(
        provider=settings.llm_provider,
        model=settings.llm_model_name,
        message=ChatMessage(role="assistant", content=final_message.content),
    )
