from app.schemas.chat import ChatRequest
from app.services.chat_service import build_chat_messages, run_chat


def test_chat_returns_stub_response() -> None:
    response = run_chat(
        ChatRequest(messages=[{"role": "user", "content": "Hello graph"}])
    )

    assert response.provider == "stub"
    assert response.model == "stub-chat-model"
    assert response.message.role == "assistant"
    assert response.message.content == "Stub reply: Hello graph"


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
            ChatRequest(messages=[{"role": "user", "content": "Config check"}])
        )
        assert response.message.content == "Configured: Config check"
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
