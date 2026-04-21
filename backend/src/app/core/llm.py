from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel, SimpleChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI

from app.core.config import settings


class StubChatModel(SimpleChatModel):
    @property
    def _llm_type(self) -> str:
        return "stub-chat-model"

    def _call(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> str:
        del stop, run_manager, kwargs
        decision_context_message = next(
            (
                message.content
                for message in reversed(messages)
                if message.type == "system"
                and "Use this structured restaurant decision context" in message.content
            ),
            None,
        )
        latest_user_message = next(
            (message.content for message in reversed(messages) if message.type == "human"),
            settings.stub_llm_default_reply,
        )
        if decision_context_message is not None:
            return f"{settings.stub_llm_response_prefix}[grounded-context] {latest_user_message}"
        return f"{settings.stub_llm_response_prefix}{latest_user_message}"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        content = self._call(messages, stop=stop, run_manager=run_manager, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


def _build_openai_chat_model() -> BaseChatModel:
    return ChatOpenAI(
        model=settings.llm_model_name,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    provider = settings.llm_provider.lower()
    if provider == "stub":
        return StubChatModel()
    if provider == "openai":
        return _build_openai_chat_model()
    raise ValueError(f"Unsupported llm_provider: {settings.llm_provider}")


def reset_chat_model() -> None:
    get_chat_model.cache_clear()
