from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.graph.graph import get_chat_graph
from app.core.config import settings
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ChatRestaurantContext


ROLE_TO_MESSAGE = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


def build_chat_messages(request: ChatRequest) -> list[SystemMessage | HumanMessage | AIMessage]:
    messages: list[SystemMessage | HumanMessage | AIMessage] = []

    if settings.chat_system_prompt:
        messages.append(SystemMessage(content=settings.chat_system_prompt))

    if request.restaurant_context is not None:
        messages.append(SystemMessage(content=_format_restaurant_context(request.restaurant_context)))

    for message in request.messages:
        message_cls = ROLE_TO_MESSAGE[message.role]
        messages.append(message_cls(content=message.content))

    return messages


def _format_restaurant_context(restaurant: ChatRestaurantContext) -> str:
    category_summary = ", ".join(restaurant.categories[:5]) if restaurant.categories else "Unknown"
    rating_summary = (
        f"{restaurant.stars:.1f}/5" if restaurant.stars is not None else "rating unavailable"
    )
    return (
        "The current conversation is about this restaurant only: "
        f"{restaurant.name} ({restaurant.business_id}) in {restaurant.city}, {restaurant.state}. "
        f"Categories: {category_summary}. Rating: {rating_summary}. "
        f"Review count: {restaurant.review_count}. "
        "Answer the user as if they are asking about this selected restaurant."
    )


def run_chat(request: ChatRequest) -> ChatResponse:
    result = get_chat_graph().invoke({"messages": build_chat_messages(request)})
    final_message = result["messages"][-1]

    return ChatResponse(
        provider=settings.llm_provider,
        model=settings.llm_model_name,
        message=ChatMessage(role="assistant", content=final_message.content),
        restaurant_context=request.restaurant_context,
    )
