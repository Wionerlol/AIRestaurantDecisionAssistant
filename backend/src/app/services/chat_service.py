from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agents.graph.graph import get_chat_graph
from app.core.config import settings
from app.schemas.chat import (
    ChatIntent,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatRestaurantContext,
)
from app.schemas.chat import (
    ChatProcessTrace,
    ChatProcessTraceEvidence,
    ChatProcessTraceIntent,
    ChatProcessTraceTool,
    ChatProcessTraceToolExecution,
    ChatProcessTraceToolPlan,
)


ROLE_TO_MESSAGE = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}

TOOL_PURPOSES = {
    "get_restaurant_profile": "Read selected restaurant profile and basic metadata.",
    "get_restaurant_aspect_summary": "Summarize restaurant-level aspect and sentiment signals.",
    "get_review_aspect_evidence": "Retrieve ranked review evidence for requested aspects or sentiment.",
    "get_negative_review_patterns": "Find recurring complaints, cons, and risk patterns.",
    "get_positive_review_patterns": "Find recurring strengths, pros, and positive evidence patterns.",
    "get_scenario_fit": "Evaluate whether the restaurant fits a specific dining scenario.",
    "get_recent_review_trend": "Check recent review trend, sentiment drift, and fresh risks.",
    "get_decision_inputs": "Combine restaurant and review signals into recommendation inputs.",
    "get_supported_intents": "List supported restaurant question types when the request is unsupported.",
}


def build_chat_messages(request: ChatRequest) -> list[SystemMessage | HumanMessage | AIMessage]:
    messages: list[SystemMessage | HumanMessage | AIMessage] = []

    if settings.chat_system_prompt:
        messages.append(SystemMessage(content=settings.chat_system_prompt))

    if request.restaurant_context is not None:
        messages.append(
            SystemMessage(content=_format_restaurant_context(request.restaurant_context))
        )

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


def build_graph_input(request: ChatRequest) -> dict:
    restaurant = request.restaurant_context
    return {
        "messages": build_chat_messages(request),
        "restaurant_business_id": restaurant.business_id if restaurant else None,
        "restaurant_name": restaurant.name if restaurant else None,
        "restaurant_city": restaurant.city if restaurant else None,
        "restaurant_state": restaurant.state if restaurant else None,
    }


def run_chat(request: ChatRequest) -> ChatResponse:
    result = get_chat_graph().invoke(build_graph_input(request))
    final_message = result["messages"][-1]

    return ChatResponse(
        provider=settings.llm_provider,
        model=settings.llm_model_name,
        message=ChatMessage(role="assistant", content=final_message.content),
        intent=ChatIntent(
            category=result["intent_category"],
            label=result["intent_label"],
        ),
        restaurant_context=request.restaurant_context,
        process_trace=build_process_trace(result),
    )


def build_process_trace(result: dict) -> ChatProcessTrace:
    intent_category = str(result["intent_category"])
    intent_label = str(result["intent_label"])
    tool_plan = result.get("tool_plan", [])
    tool_results = result.get("tool_results", {})
    missing_evidence_notes = result.get("missing_evidence_notes", [])
    evidence_coverage = result.get("evidence_coverage", {})

    return ChatProcessTrace(
        intent=ChatProcessTraceIntent(
            category=intent_category,
            label=intent_label,
            summary=_intent_trace_summary(intent_category, intent_label),
        ),
        tool_plan=ChatProcessTraceToolPlan(
            reason=result.get("tool_plan_reason"),
            tools=[
                ChatProcessTraceTool(
                    name=str(tool_call.get("name", "unknown")),
                    purpose=TOOL_PURPOSES.get(
                        str(tool_call.get("name", "")),
                        "Run a restaurant decision helper tool.",
                    ),
                )
                for tool_call in tool_plan
                if isinstance(tool_call, dict)
            ],
        ),
        tool_execution=_build_tool_execution_trace(tool_plan, tool_results),
        evidence=ChatProcessTraceEvidence(
            coverage={
                str(key): bool(value)
                for key, value in evidence_coverage.items()
                if isinstance(key, str)
            },
            missing=[str(note) for note in missing_evidence_notes],
        ),
        answer_basis=_build_answer_basis_trace(result),
    )


def _intent_trace_summary(intent_category: str, intent_label: str) -> str:
    if intent_category == "greeting":
        return "Recognized a greeting, so no restaurant database tools were needed."
    if intent_category == "unknown":
        return "The request did not match a supported restaurant decision intent."
    return f"Recognized this as a {intent_category} question with label {intent_label}."


def _build_tool_execution_trace(
    tool_plan: list[dict],
    tool_results: dict,
) -> list[ChatProcessTraceToolExecution]:
    execution_trace = []
    for tool_call in tool_plan:
        if not isinstance(tool_call, dict):
            continue
        tool_name = str(tool_call.get("name", "unknown"))
        result = tool_results.get(tool_name, {})
        status = str(result.get("status", "not_run")) if isinstance(result, dict) else "not_run"
        execution_trace.append(
            ChatProcessTraceToolExecution(
                name=tool_name,
                status=status,
                summary=_tool_execution_summary(tool_name, status, result),
            )
        )
    return execution_trace


def _tool_execution_summary(tool_name: str, status: str, result: object) -> str:
    if status == "ok":
        return f"{TOOL_PURPOSES.get(tool_name, 'Tool')} completed and returned usable evidence."
    if status == "empty":
        return f"{TOOL_PURPOSES.get(tool_name, 'Tool')} ran but found no matching evidence."
    if status == "skipped":
        errors = result.get("errors", []) if isinstance(result, dict) else []
        reason = str(errors[0]) if errors else "Required context was missing."
        return f"Skipped because {reason}"
    if status == "error":
        return "The tool failed, so its evidence was not used."
    return "The tool was planned but did not run."


def _build_answer_basis_trace(result: dict) -> list[str]:
    intent_label = str(result["intent_label"])
    answer_hints = (
        result.get("decision_context", {}).get("answer_hints", [])
        if isinstance(result.get("decision_context"), dict)
        else []
    )
    basis = [str(hint) for hint in answer_hints[:4]]

    if not basis and intent_label == "greeting":
        basis.append(
            "Respond with a short greeting and explain what restaurant questions are supported."
        )
    if not basis and intent_label == "unsupported":
        basis.append(
            "Explain the supported restaurant question types instead of using database tools."
        )
    if not basis:
        basis.append(
            "Use available tool evidence to answer the user's restaurant question directly."
        )

    return basis
