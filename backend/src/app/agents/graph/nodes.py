from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents.graph.state import ChatGraphState
from app.core.llm import get_chat_model
from app.services.intent_service import classify_intent


INTENT_TOOL_PLANS: dict[str, list[dict[str, object]]] = {
    "worth_it": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_restaurant_aspect_summary", "args": {}},
        {"name": "get_positive_review_patterns", "args": {}},
        {"name": "get_negative_review_patterns", "args": {}},
        {"name": "get_decision_inputs", "args": {"intent_label": "worth_it"}},
    ],
    "should_go": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_restaurant_aspect_summary", "args": {}},
        {"name": "get_negative_review_patterns", "args": {}},
        {"name": "get_decision_inputs", "args": {"intent_label": "should_go"}},
    ],
    "food": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_restaurant_aspect_summary", "args": {}},
        {"name": "get_review_aspect_evidence", "args": {"aspect": "food"}},
    ],
    "service": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_restaurant_aspect_summary", "args": {}},
        {"name": "get_review_aspect_evidence", "args": {"aspect": "service"}},
        {"name": "get_negative_review_patterns", "args": {"aspect": "service"}},
    ],
    "price": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_restaurant_aspect_summary", "args": {}},
        {"name": "get_review_aspect_evidence", "args": {"aspect": "price"}},
    ],
    "ambience": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_restaurant_aspect_summary", "args": {}},
        {"name": "get_review_aspect_evidence", "args": {"aspect": "ambience"}},
    ],
    "date": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_scenario_fit", "args": {"scenario": "date"}},
        {
            "name": "get_review_aspect_evidence",
            "args": {"aspects": ["ambience", "service", "price", "waiting_time"]},
        },
        {"name": "get_negative_review_patterns", "args": {}},
    ],
    "family": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_scenario_fit", "args": {"scenario": "family"}},
        {"name": "get_negative_review_patterns", "args": {}},
    ],
    "quick_meal": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_scenario_fit", "args": {"scenario": "quick_meal"}},
        {"name": "get_recent_review_trend", "args": {}},
    ],
    "complaints": [
        {"name": "get_negative_review_patterns", "args": {}},
        {"name": "get_review_aspect_evidence", "args": {"sentiment": "negative"}},
        {"name": "get_recent_review_trend", "args": {}},
    ],
    "warnings": [
        {"name": "get_restaurant_aspect_summary", "args": {}},
        {"name": "get_negative_review_patterns", "args": {}},
        {"name": "get_recent_review_trend", "args": {}},
    ],
    "summary": [
        {"name": "get_restaurant_profile", "args": {}},
        {"name": "get_restaurant_aspect_summary", "args": {}},
        {"name": "get_positive_review_patterns", "args": {}},
        {"name": "get_negative_review_patterns", "args": {}},
        {"name": "get_recent_review_trend", "args": {}},
    ],
    "unsupported": [
        {"name": "get_supported_intents", "args": {}},
    ],
}


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


def select_tools_for_intent(state: ChatGraphState) -> ChatGraphState:
    intent_label = state["intent_label"]
    tool_plan = INTENT_TOOL_PLANS.get(intent_label, INTENT_TOOL_PLANS["unsupported"])

    if intent_label == "unsupported":
        return {
            "tool_plan": tool_plan,
            "tool_plan_reason": "The intent is unsupported, so only supported-intent guidance is needed.",
            "unsupported_reason": "Unsupported restaurant question.",
        }

    return {
        "tool_plan": tool_plan,
        "tool_plan_reason": f"Selected tools for supported intent label: {intent_label}.",
        "unsupported_reason": None,
    }


def run_restaurant_tools(state: ChatGraphState) -> ChatGraphState:
    tool_results = {
        tool_call["name"]: {
            "status": "not_implemented",
            "args": {
                "business_id": state.get("restaurant_business_id"),
                **dict(tool_call.get("args", {})),
            },
        }
        for tool_call in state.get("tool_plan", [])
    }

    return {
        "tool_results": tool_results,
        "tool_errors": [],
        "evidence_coverage": {
            "has_restaurant_profile": "get_restaurant_profile" in tool_results,
            "has_restaurant_summary": "get_restaurant_aspect_summary" in tool_results,
            "has_review_evidence": "get_review_aspect_evidence" in tool_results,
            "has_scenario_fit": "get_scenario_fit" in tool_results,
        },
    }


def compose_decision_context(state: ChatGraphState) -> ChatGraphState:
    coverage = state.get("evidence_coverage", {})
    missing_evidence_notes = [
        key.removeprefix("has_").replace("_", " ")
        for key, is_present in coverage.items()
        if not is_present
    ]

    return {
        "decision_context": {
            "restaurant": {
                "business_id": state.get("restaurant_business_id"),
                "name": state.get("restaurant_name"),
                "city": state.get("restaurant_city"),
                "state": state.get("restaurant_state"),
            },
            "intent": {
                "category": state["intent_category"],
                "label": state["intent_label"],
            },
            "tool_results": state.get("tool_results", {}),
            "coverage": coverage,
        },
        "answer_requirements": {
            "stay_scoped_to_selected_restaurant": True,
            "include_risk_warnings": state["intent_label"]
            in {"worth_it", "should_go", "date", "family", "complaints", "warnings", "summary"},
            "mention_evidence_limitations": bool(missing_evidence_notes),
        },
        "missing_evidence_notes": missing_evidence_notes,
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
