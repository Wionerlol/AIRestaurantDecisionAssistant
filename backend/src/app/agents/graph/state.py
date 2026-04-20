from __future__ import annotations

from typing import Annotated, Any, NotRequired, TypedDict

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
    tool_plan: NotRequired[list[dict[str, Any]]]
    tool_plan_reason: NotRequired[str]
    unsupported_reason: NotRequired[str | None]
    tool_results: NotRequired[dict[str, Any]]
    tool_errors: NotRequired[list[str]]
    evidence_coverage: NotRequired[dict[str, bool]]
    decision_context: NotRequired[dict[str, Any]]
    answer_requirements: NotRequired[dict[str, Any]]
    missing_evidence_notes: NotRequired[list[str]]
