from sqlalchemy.orm import Session

from app.agents.graph.graph import get_chat_graph
from app.agents.graph.nodes import _build_decision_context_message
from app.schemas.chat import ChatRequest
from app.services.chat_service import build_chat_messages, build_graph_input, run_chat
from app.services.intent_service import classify_intent
from app.services.restaurant_service import list_restaurants


def test_chat_returns_stub_response() -> None:
    response = run_chat(ChatRequest(messages=[{"role": "user", "content": "Hello graph"}]))

    assert response.provider == "stub"
    assert response.model == "stub-chat-model"
    assert response.message.role == "assistant"
    assert response.intent.category == "unknown"
    assert response.intent.label == "unsupported"
    assert (
        "Sorry, I can only help with a fixed set of restaurant questions right now."
        in response.message.content
    )
    assert "Is this restaurant worth it?" in response.message.content


def test_chat_includes_configurable_stub_prefix() -> None:
    from app.agents.graph.graph import reset_chat_graph
    from app.core.config import settings
    from app.core.llm import reset_chat_model

    original_prefix = settings.stub_llm_response_prefix
    settings.stub_llm_response_prefix = "Configured: "
    reset_chat_model()
    reset_chat_graph()

    try:
        response = run_chat(
            ChatRequest(messages=[{"role": "user", "content": "How is the service here?"}])
        )
        assert response.message.content == "Configured: [grounded-context] How is the service here?"
    finally:
        settings.stub_llm_response_prefix = original_prefix
        reset_chat_model()
        reset_chat_graph()


def test_chat_request_can_include_restaurant_context() -> None:
    request = ChatRequest(
        restaurant_context={
            "business_id": "restaurant-1",
            "name": "Demo Bistro",
            "city": "Philadelphia",
            "state": "PA",
            "stars": 4.5,
            "review_count": 120,
            "categories": ["Restaurants", "French"],
        },
        messages=[{"role": "user", "content": "Is this place good for dinner?"}],
    )

    messages = build_chat_messages(request)

    assert messages[1].type == "system"
    assert "Demo Bistro" in messages[1].content
    assert "Philadelphia" in messages[1].content
    assert "French" in messages[1].content


def test_chat_response_preserves_restaurant_context() -> None:
    response = run_chat(
        ChatRequest(
            restaurant_context={
                "business_id": "restaurant-1",
                "name": "Demo Bistro",
                "city": "Philadelphia",
                "state": "PA",
                "stars": 4.5,
                "review_count": 120,
                "categories": ["Restaurants", "French"],
            },
            messages=[{"role": "user", "content": "Should I go?"}],
        )
    )

    assert response.restaurant_context is not None
    assert response.restaurant_context.name == "Demo Bistro"
    assert response.restaurant_context.business_id == "restaurant-1"


def test_graph_input_includes_restaurant_identity_fields() -> None:
    graph_input = build_graph_input(
        ChatRequest(
            restaurant_context={
                "business_id": "restaurant-1",
                "name": "Demo Bistro",
                "city": "Philadelphia",
                "state": "PA",
                "stars": 4.5,
                "review_count": 120,
                "categories": ["Restaurants", "French"],
            },
            messages=[{"role": "user", "content": "Should I go?"}],
        )
    )

    assert graph_input["restaurant_business_id"] == "restaurant-1"
    assert graph_input["restaurant_name"] == "Demo Bistro"
    assert graph_input["restaurant_city"] == "Philadelphia"
    assert graph_input["restaurant_state"] == "PA"


def test_intent_classifier_detects_category_and_label_pairs() -> None:
    assert classify_intent("Is this restaurant worth it?").model_dump() == {
        "category": "recommendation",
        "label": "worth_it",
    }
    assert classify_intent("How is the food here?").model_dump() == {
        "category": "aspect",
        "label": "food",
    }
    assert classify_intent("Is it good for a date?").model_dump() == {
        "category": "scenario",
        "label": "date",
    }
    assert classify_intent("Any common complaints?").model_dump() == {
        "category": "risk",
        "label": "complaints",
    }
    assert classify_intent("Give me a summary").model_dump() == {
        "category": "summary",
        "label": "summary",
    }
    assert classify_intent("你好").model_dump() == {
        "category": "greeting",
        "label": "greeting",
    }
    assert classify_intent("Tell me something random").model_dump() == {
        "category": "unknown",
        "label": "unsupported",
    }


def test_supported_intent_still_uses_stub_model_response() -> None:
    response = run_chat(
        ChatRequest(messages=[{"role": "user", "content": "How is the food here?"}])
    )

    assert response.intent.category == "aspect"
    assert response.intent.label == "food"
    assert response.message.content == "Stub reply: [grounded-context] How is the food here?"
    assert response.process_trace.intent.label == "food"
    assert [tool.name for tool in response.process_trace.tool_plan.tools] == [
        "get_restaurant_profile",
        "get_restaurant_aspect_summary",
        "get_review_aspect_evidence",
    ]
    assert response.process_trace.tool_execution[0].status == "skipped"
    assert "State evidence limitations" in response.process_trace.answer_basis[0]


def test_supported_intent_builds_tool_plan_and_executes_tools(
    db_session: Session,
) -> None:
    restaurant = list_restaurants(db_session, limit=1)[0]

    result = get_chat_graph().invoke(
        build_graph_input(
            ChatRequest(
                restaurant_context={
                    "business_id": restaurant.business_id,
                    "name": restaurant.name,
                    "city": restaurant.city,
                    "state": restaurant.state,
                    "stars": restaurant.stars,
                    "review_count": restaurant.review_count,
                    "categories": restaurant.categories,
                },
                messages=[{"role": "user", "content": "Is it good for a date?"}],
            )
        )
    )

    assert result["intent_label"] == "date"
    assert [tool_call["name"] for tool_call in result["tool_plan"]] == [
        "get_restaurant_profile",
        "get_scenario_fit",
        "get_review_aspect_evidence",
        "get_negative_review_patterns",
    ]
    assert result["tool_results"]["get_scenario_fit"]["args"] == {
        "business_id": restaurant.business_id,
        "scenario": "date",
    }
    assert result["tool_results"]["get_restaurant_profile"]["status"] == "ok"
    assert result["tool_results"]["get_restaurant_profile"]["data"]["business_id"] == (
        restaurant.business_id
    )
    assert result["tool_results"]["get_scenario_fit"]["tool_name"] == "get_scenario_fit"
    assert result["tool_results"]["get_scenario_fit"]["status"] == "ok"
    assert result["tool_errors"] == []
    assert result["evidence_coverage"]["has_restaurant_profile"] is True
    assert result["evidence_coverage"]["has_scenario_fit"] is True
    assert result["decision_context"]["restaurant"]["business_id"] == restaurant.business_id
    assert result["decision_context"]["intent"] == {
        "category": "scenario",
        "label": "date",
    }
    assert result["decision_context"]["profile"]["business_id"] == restaurant.business_id
    assert result["decision_context"]["scenario_fit"]["scenario"] == "date"
    assert result["decision_context"]["scenario_fit"]["fit_label"] in {
        "good_fit",
        "mixed_fit",
        "poor_fit",
        "insufficient_data",
    }
    assert result["decision_context"]["review_evidence"]["total"] >= 0
    assert "top_cons" in result["decision_context"]["negative_patterns"]
    assert isinstance(result["decision_context"]["risks"], list)
    assert "Use scenario fit label:" in " ".join(result["decision_context"]["answer_hints"])
    assert result["answer_requirements"]["include_risk_warnings"] is True
    assert result["messages"][-1].content == (
        "Stub reply: [grounded-context] Is it good for a date?"
    )


def test_supported_intent_without_restaurant_context_skips_database_tools() -> None:
    result = get_chat_graph().invoke(
        build_graph_input(ChatRequest(messages=[{"role": "user", "content": "How is the food?"}]))
    )

    assert result["intent_label"] == "food"
    assert result["tool_results"]["get_restaurant_profile"]["status"] == "skipped"
    assert result["tool_results"]["get_review_aspect_evidence"]["status"] == "skipped"
    assert result["tool_errors"] == [
        "Missing restaurant business_id for tool: get_restaurant_profile",
        "Missing restaurant business_id for tool: get_restaurant_aspect_summary",
        "Missing restaurant business_id for tool: get_review_aspect_evidence",
    ]
    assert result["evidence_coverage"]["has_restaurant_profile"] is False
    assert result["evidence_coverage"]["has_review_evidence"] is False
    assert result["decision_context"]["profile"] is None
    assert result["decision_context"]["review_evidence"] == {}
    assert result["decision_context"]["answer_hints"] == [
        "State evidence limitations for missing planned tool outputs."
    ]
    assert result["messages"][-1].content == ("Stub reply: [grounded-context] How is the food?")


def test_decision_context_prompt_requires_conversational_evidence_grounded_answer() -> None:
    message = _build_decision_context_message(
        {
            "decision_context": {
                "intent": {"category": "scenario", "label": "date"},
                "scenario_fit": {"fit_label": "mixed_fit"},
                "risks": ["long wait"],
            },
            "answer_requirements": {
                "include_risk_warnings": True,
                "mention_evidence_limitations": False,
            },
            "missing_evidence_notes": [],
            "tool_errors": [],
        }
    )

    assert message.type == "system"
    assert "Match the user's language" in message.content
    assert "answer in natural, conversational Chinese" in message.content
    assert "Start with a direct answer" in message.content
    assert "2-4 concise evidence-backed reasons" in message.content
    assert "Mention risks or caveats" in message.content
    assert "Intent-specific guidance" in message.content
    assert "date/family/quick_meal" in message.content
    assert "Do not expose raw JSON" in message.content


def test_unknown_intent_bypasses_restaurant_tool_nodes() -> None:
    result = get_chat_graph().invoke(
        build_graph_input(
            ChatRequest(messages=[{"role": "user", "content": "Tell me something random"}])
        )
    )

    assert result["intent_label"] == "unsupported"
    assert "tool_plan" not in result
    assert "decision_context" not in result
    assert "Sorry, I can only help with a fixed set of restaurant questions right now." in (
        result["messages"][-1].content
    )


def test_greeting_intent_bypasses_restaurant_tool_nodes() -> None:
    result = get_chat_graph().invoke(
        build_graph_input(ChatRequest(messages=[{"role": "user", "content": "hi"}]))
    )

    assert result["intent_category"] == "greeting"
    assert result["intent_label"] == "greeting"
    assert "tool_plan" not in result
    assert "decision_context" not in result
    assert "Pick a restaurant first" in result["messages"][-1].content


def test_chat_response_includes_process_trace_for_greeting() -> None:
    response = run_chat(ChatRequest(messages=[{"role": "user", "content": "hi"}]))

    assert response.intent.category == "greeting"
    assert response.process_trace.intent.summary == (
        "Recognized a greeting, so no restaurant database tools were needed."
    )
    assert response.process_trace.tool_plan.tools == []
    assert response.process_trace.tool_execution == []
    assert response.process_trace.evidence.coverage == {}
    assert "short greeting" in response.process_trace.answer_basis[0]
