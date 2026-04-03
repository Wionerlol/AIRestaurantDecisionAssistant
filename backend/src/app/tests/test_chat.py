from app.schemas.chat import ChatRequest
from app.services.intent_service import classify_intent
from app.services.chat_service import build_chat_messages, run_chat


def test_chat_returns_stub_response() -> None:
    response = run_chat(
        ChatRequest(messages=[{"role": "user", "content": "Hello graph"}])
    )

    assert response.provider == "stub"
    assert response.model == "stub-chat-model"
    assert response.message.role == "assistant"
    assert response.intent.category == "unknown"
    assert response.intent.label == "unsupported"
    assert "Sorry, I can only help with a fixed set of restaurant questions right now." in response.message.content
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
        assert response.message.content == "Configured: How is the service here?"
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
    assert response.message.content == "Stub reply: How is the food here?"
