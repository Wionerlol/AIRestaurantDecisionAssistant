from __future__ import annotations

from collections.abc import Callable
from typing import Any

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

RESTAURANT_CONTEXT_TOOLS = {
    "get_restaurant_profile",
    "get_restaurant_aspect_summary",
    "get_review_aspect_evidence",
    "get_negative_review_patterns",
    "get_positive_review_patterns",
    "get_scenario_fit",
    "get_recent_review_trend",
    "get_decision_inputs",
}

TOOL_COVERAGE_KEYS = {
    "get_restaurant_profile": "has_restaurant_profile",
    "get_restaurant_aspect_summary": "has_restaurant_summary",
    "get_review_aspect_evidence": "has_review_evidence",
    "get_positive_review_patterns": "has_positive_patterns",
    "get_negative_review_patterns": "has_negative_patterns",
    "get_recent_review_trend": "has_recent_trend",
    "get_scenario_fit": "has_scenario_fit",
    "get_decision_inputs": "has_decision_inputs",
    "get_supported_intents": "has_supported_intents",
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
    tool_results = {}
    tool_errors = []
    tool_registry = _get_tool_registry()

    for tool_call in state.get("tool_plan", []):
        tool_name = str(tool_call["name"])
        tool_args = {
            "business_id": state.get("restaurant_business_id"),
            **dict(tool_call.get("args", {})),
        }
        tool = tool_registry.get(tool_name)

        if tool is None:
            error = f"Tool is not registered: {tool_name}"
            tool_results[tool_name] = {
                "tool_name": tool_name,
                "status": "error",
                "args": tool_args,
                "errors": [error],
            }
            tool_errors.append(error)
            continue

        if tool_name in RESTAURANT_CONTEXT_TOOLS and not tool_args.get("business_id"):
            error = f"Missing restaurant business_id for tool: {tool_name}"
            tool_results[tool_name] = {
                "tool_name": tool_name,
                "status": "skipped",
                "args": tool_args,
                "errors": [error],
            }
            tool_errors.append(error)
            continue

        try:
            invoke_args = (
                tool_args
                if tool_name in RESTAURANT_CONTEXT_TOOLS
                else dict(tool_call.get("args", {}))
            )
            result = tool.invoke(invoke_args)
            if isinstance(result, dict):
                tool_results[tool_name] = {
                    **result,
                    "args": invoke_args,
                }
            else:
                tool_results[tool_name] = {
                    "tool_name": tool_name,
                    "status": "ok",
                    "data": result,
                    "args": invoke_args,
                    "errors": [],
                }
        except Exception as exc:  # pragma: no cover - defensive isolation for graph runtime
            error = f"{tool_name} failed: {exc}"
            tool_results[tool_name] = {
                "tool_name": tool_name,
                "status": "error",
                "args": tool_args,
                "errors": [error],
            }
            tool_errors.append(error)

    return {
        "tool_results": tool_results,
        "tool_errors": tool_errors,
        "evidence_coverage": _build_evidence_coverage(tool_results),
    }


def _get_tool_registry() -> dict[str, Any]:
    from app.agents.tools.decision_inputs import get_decision_inputs_tool
    from app.agents.tools.negative_review_patterns import get_negative_review_patterns_tool
    from app.agents.tools.positive_review_patterns import get_positive_review_patterns_tool
    from app.agents.tools.recent_review_trend import get_recent_review_trend_tool
    from app.agents.tools.restaurant_aspect_summary import get_restaurant_aspect_summary_tool
    from app.agents.tools.restaurant_profile import get_restaurant_profile_tool
    from app.agents.tools.review_aspect_evidence import get_review_aspect_evidence_tool
    from app.agents.tools.scenario_fit import get_scenario_fit_tool
    from app.agents.tools.supported_intents import get_supported_intents_tool

    return {
        "get_restaurant_profile": get_restaurant_profile_tool,
        "get_restaurant_aspect_summary": get_restaurant_aspect_summary_tool,
        "get_review_aspect_evidence": get_review_aspect_evidence_tool,
        "get_negative_review_patterns": get_negative_review_patterns_tool,
        "get_positive_review_patterns": get_positive_review_patterns_tool,
        "get_scenario_fit": get_scenario_fit_tool,
        "get_recent_review_trend": get_recent_review_trend_tool,
        "get_decision_inputs": get_decision_inputs_tool,
        "get_supported_intents": get_supported_intents_tool,
    }


def _build_evidence_coverage(tool_results: dict[str, Any]) -> dict[str, bool]:
    def has_usable_result(tool_name: str) -> bool:
        result = tool_results.get(tool_name)
        return isinstance(result, dict) and result.get("status") in {"ok", "empty"}

    coverage_checks: dict[str, Callable[[], bool]] = {
        "has_restaurant_profile": lambda: has_usable_result("get_restaurant_profile"),
        "has_restaurant_summary": lambda: has_usable_result("get_restaurant_aspect_summary"),
        "has_review_evidence": lambda: has_usable_result("get_review_aspect_evidence"),
        "has_positive_patterns": lambda: has_usable_result("get_positive_review_patterns"),
        "has_negative_patterns": lambda: has_usable_result("get_negative_review_patterns"),
        "has_recent_trend": lambda: has_usable_result("get_recent_review_trend"),
        "has_scenario_fit": lambda: has_usable_result("get_scenario_fit"),
        "has_decision_inputs": lambda: has_usable_result("get_decision_inputs"),
        "has_supported_intents": lambda: has_usable_result("get_supported_intents"),
    }
    return {name: check() for name, check in coverage_checks.items()}


def compose_decision_context(state: ChatGraphState) -> ChatGraphState:
    coverage = state.get("evidence_coverage", {})
    tool_results = state.get("tool_results", {})
    planned_coverage_keys = {
        TOOL_COVERAGE_KEYS[tool_call["name"]]
        for tool_call in state.get("tool_plan", [])
        if tool_call["name"] in TOOL_COVERAGE_KEYS
    }
    missing_evidence_notes = [
        key.removeprefix("has_").replace("_", " ")
        for key, is_present in coverage.items()
        if key in planned_coverage_keys and not is_present
    ]
    normalized_context = _normalize_tool_outputs(tool_results)
    answer_hints = _build_answer_hints(
        state["intent_label"],
        normalized_context,
        missing_evidence_notes,
    )

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
            **normalized_context,
            "answer_hints": answer_hints,
            "tool_results": tool_results,
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


def _normalize_tool_outputs(tool_results: dict[str, Any]) -> dict[str, Any]:
    profile = _tool_data(tool_results, "get_restaurant_profile")
    aspect_summary = _tool_data(tool_results, "get_restaurant_aspect_summary")
    decision = _decision_context(_tool_data(tool_results, "get_decision_inputs"))
    scenario_fit = _scenario_context(_tool_data(tool_results, "get_scenario_fit"))
    review_evidence = _review_evidence_context(
        _tool_data(tool_results, "get_review_aspect_evidence")
    )
    positive_patterns = _positive_patterns_context(
        _tool_data(tool_results, "get_positive_review_patterns")
    )
    negative_patterns = _negative_patterns_context(
        _tool_data(tool_results, "get_negative_review_patterns")
    )
    recent_trend = _recent_trend_context(_tool_data(tool_results, "get_recent_review_trend"))
    supported_intents = _tool_data(tool_results, "get_supported_intents")
    risks = _merge_unique(
        [
            *(aspect_summary or {}).get("risk_flags", []),
            *negative_patterns.get("top_risk_flags", []),
            *scenario_fit.get("risk_flags", []),
            *decision.get("risk_flags", []),
            *recent_trend.get("recent_risk_flags", []),
        ]
    )

    return {
        "profile": profile,
        "aspect_summary": aspect_summary,
        "decision": decision,
        "scenario_fit": scenario_fit,
        "review_evidence": review_evidence,
        "positive_patterns": positive_patterns,
        "negative_patterns": negative_patterns,
        "recent_trend": recent_trend,
        "risks": risks,
        "supported_intents": supported_intents,
    }


def _tool_data(tool_results: dict[str, Any], tool_name: str) -> dict[str, Any] | None:
    result = tool_results.get(tool_name)
    if not isinstance(result, dict) or result.get("status") not in {"ok", "empty"}:
        return None
    data = result.get("data")
    return data if isinstance(data, dict) else None


def _decision_context(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    return {
        "intent_label": data.get("intent_label"),
        "decision_score": data.get("decision_score"),
        "decision_label": data.get("decision_label"),
        "strengths": data.get("strengths", []),
        "weaknesses": data.get("weaknesses", []),
        "risk_flags": data.get("risk_flags", []),
        "aspect_scores": data.get("aspect_scores", {}),
        "sentiment_label_counts": data.get("sentiment_label_counts", {}),
        "coverage": data.get("coverage", {}),
    }


def _scenario_context(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    return {
        "scenario": data.get("scenario"),
        "fit_score": data.get("fit_score"),
        "fit_label": data.get("fit_label"),
        "supporting_reasons": data.get("supporting_reasons", []),
        "opposing_reasons": data.get("opposing_reasons", []),
        "risk_flags": data.get("risk_flags", []),
        "aspect_scores": data.get("aspect_scores", {}),
        "positive_evidence": _compact_evidence_items(data.get("positive_evidence", [])),
        "negative_evidence": _compact_evidence_items(data.get("negative_evidence", [])),
    }


def _review_evidence_context(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    return {
        "aspect": data.get("aspect"),
        "aspects": data.get("aspects", []),
        "sentiment": data.get("sentiment"),
        "total": data.get("total", 0),
        "items": _compact_evidence_items(data.get("items", [])),
    }


def _positive_patterns_context(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    return {
        "aspect": data.get("aspect"),
        "total": data.get("total", 0),
        "top_pros": data.get("top_pros", []),
        "top_evidence_terms": data.get("top_evidence_terms", []),
        "items": _compact_evidence_items(data.get("items", [])),
    }


def _negative_patterns_context(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    return {
        "aspect": data.get("aspect"),
        "total": data.get("total", 0),
        "top_cons": data.get("top_cons", []),
        "top_risk_flags": data.get("top_risk_flags", []),
        "top_evidence_terms": data.get("top_evidence_terms", []),
        "items": _compact_evidence_items(data.get("items", [])),
    }


def _recent_trend_context(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    recent_risk_flags = _merge_unique(
        [flag for item in data.get("items", []) for flag in item.get("risk_flags", [])]
    )
    return {
        "months": data.get("months"),
        "total": data.get("total", 0),
        "average_stars": data.get("average_stars"),
        "average_sentiment_score": data.get("average_sentiment_score"),
        "sentiment_label_counts": data.get("sentiment_label_counts", {}),
        "star_trend": data.get("star_trend"),
        "aspect_average_scores": data.get("aspect_average_scores", {}),
        "recent_risk_flags": recent_risk_flags,
        "items": _compact_evidence_items(data.get("items", [])),
    }


def _compact_evidence_items(items: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    compact_items = []
    for item in items[:limit]:
        compact_items.append(
            {
                "review_id": item.get("review_id"),
                "stars": item.get("stars"),
                "text": item.get("text"),
                "review_date": item.get("review_date"),
                "relevance_score": item.get("relevance_score"),
                "matched_keywords": item.get("matched_keywords", []),
                "evidence_terms": item.get("evidence_terms", []),
                "pros": item.get("pros", []),
                "cons": item.get("cons", []),
                "risk_flags": item.get("risk_flags", []),
            }
        )
    return compact_items


def _build_answer_hints(
    intent_label: str,
    normalized_context: dict[str, Any],
    missing_evidence_notes: list[str],
) -> list[str]:
    hints = []
    decision = normalized_context["decision"]
    scenario_fit = normalized_context["scenario_fit"]
    risks = normalized_context["risks"]

    if decision.get("decision_label"):
        hints.append(f"Use decision label: {decision['decision_label']}.")
    if scenario_fit.get("fit_label"):
        hints.append(f"Use scenario fit label: {scenario_fit['fit_label']}.")
    if risks:
        hints.append("Mention the most relevant risk flags.")
    if intent_label in {"worth_it", "should_go"}:
        hints.append("Balance positive and negative evidence before giving a recommendation.")
    if intent_label in {"complaints", "warnings"}:
        hints.append("Prioritize complaints, risks, and recent negative signals.")
    if missing_evidence_notes:
        hints.append("State evidence limitations for missing planned tool outputs.")
    return hints


def _merge_unique(values: list[str]) -> list[str]:
    seen = set()
    merged = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            merged.append(value)
    return merged


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
