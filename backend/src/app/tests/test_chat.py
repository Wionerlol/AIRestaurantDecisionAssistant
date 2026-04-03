from app.schemas.chat import ChatRequest
from app.services.chat_service import run_chat


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
