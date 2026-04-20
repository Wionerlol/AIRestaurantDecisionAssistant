from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class ChatGraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent_category: str
    intent_label: str
    restaurant_business_id: str | None
    restaurant_name: str | None
    restaurant_city: str | None
    restaurant_state: str | None
