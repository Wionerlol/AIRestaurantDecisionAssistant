from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.llm import get_chat_model
from app.schemas.chat import ChatIntent


SUPPORTED_INTENTS = {
    "worth_it": "recommendation",
    "should_go": "recommendation",
    "food": "aspect",
    "service": "aspect",
    "price": "aspect",
    "ambience": "aspect",
    "date": "scenario",
    "family": "scenario",
    "quick_meal": "scenario",
    "complaints": "risk",
    "warnings": "risk",
    "summary": "summary",
    "greeting": "greeting",
    "unsupported": "unknown",
}

KEYWORD_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("recommendation", "worth_it", ("worth it", "worth trying", "worth going")),
    ("recommendation", "should_go", ("should i go", "go or skip", "should go", "skip")),
    ("aspect", "food", ("food", "dish", "meal", "taste", "menu")),
    ("aspect", "service", ("service", "staff", "waiter", "waitress", "server")),
    ("aspect", "price", ("price", "expensive", "cheap", "value", "cost", "priced")),
    ("aspect", "ambience", ("ambience", "atmosphere", "vibe", "romantic", "noise")),
    ("scenario", "date", ("date", "romantic", "anniversary")),
    ("scenario", "family", ("family", "kids", "children", "parents")),
    ("scenario", "quick_meal", ("quick meal", "quick bite", "fast", "takeout", "take-out")),
    ("risk", "complaints", ("complaint", "complaints", "common issue", "negative", "bad")),
    ("risk", "warnings", ("warning", "warnings", "watch out", "avoid", "risk")),
]


def classify_intent(text: str) -> ChatIntent:
    if settings.llm_provider.lower() != "stub":
        llm_intent = _classify_intent_with_llm(text)
        if llm_intent is not None:
            return llm_intent
    return classify_intent_with_rules(text)


def classify_intent_with_rules(text: str) -> ChatIntent:
    normalized = text.strip().lower()

    if _is_greeting(normalized):
        return ChatIntent(category="greeting", label="greeting")

    if "summary" in normalized or "summarize" in normalized or "overview" in normalized:
        return ChatIntent(category="summary", label="summary")

    for category, label, keywords in KEYWORD_RULES:
        if any(keyword in normalized for keyword in keywords):
            return ChatIntent(category=category, label=label)

    return ChatIntent(category="unknown", label="unsupported")


def _classify_intent_with_llm(text: str) -> ChatIntent | None:
    prompt = (
        "You classify a user's restaurant-assistant message into exactly one supported intent.\n"
        "Return strict JSON only, with keys: category, label, reason.\n\n"
        "Supported labels:\n"
        "- recommendation/worth_it: asks if the selected restaurant is worth trying or worth the money.\n"
        "- recommendation/should_go: asks whether to go, skip, or decide yes/no.\n"
        "- aspect/food: asks about food, dishes, taste, menu, portions, drinks, dessert.\n"
        "- aspect/service: asks about staff, service, waiters, reservations, hospitality.\n"
        "- aspect/price: asks about price, value, expensive, cheap, cost, budget.\n"
        "- aspect/ambience: asks about vibe, atmosphere, noise, decor, seating, romance.\n"
        "- scenario/date: asks whether it fits a date, romantic meal, anniversary, couples.\n"
        "- scenario/family: asks whether it fits family, kids, parents, baby, children.\n"
        "- scenario/quick_meal: asks whether it fits a quick meal, quick bite, takeout, lunch break.\n"
        "- risk/complaints: asks what people complain about or negative reviews.\n"
        "- risk/warnings: asks for watch-outs, red flags, risks, avoid/避雷.\n"
        "- summary/summary: asks for a summary or overview.\n"
        "- greeting/greeting: short greeting or small talk without a restaurant question.\n"
        "- unknown/unsupported: not a restaurant decision question.\n\n"
        "Rules:\n"
        "- Choose the most specific label.\n"
        "- If the message is only hello/hi/你好, use greeting/greeting.\n"
        "- If it asks a supported restaurant question in Chinese, classify it normally.\n"
        "- Do not invent labels outside the supported list."
    )
    try:
        response = get_chat_model().invoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content=f"User message: {text}"),
            ]
        )
        payload = _parse_json_object(str(response.content))
        label = str(payload.get("label", "unsupported"))
        category = str(payload.get("category", SUPPORTED_INTENTS.get(label, "unknown")))
        if SUPPORTED_INTENTS.get(label) != category:
            return None
        return ChatIntent(category=category, label=label)
    except Exception:
        return None


def _parse_json_object(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object found.")
    return json.loads(cleaned[start : end + 1])


def _is_greeting(normalized: str) -> bool:
    if not normalized or len(normalized) > 80:
        return False
    restaurant_keywords = (
        "worth",
        "food",
        "service",
        "review",
        "restaurant",
        "price",
        "date",
        "family",
        "summary",
        "值得",
        "好吃",
        "餐厅",
        "饭店",
    )
    if any(keyword in normalized for keyword in restaurant_keywords):
        return False
    return normalized.strip(" !?.。,，") in {"hello", "hi", "hey", "你好", "您好"}
