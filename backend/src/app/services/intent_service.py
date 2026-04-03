from __future__ import annotations

from app.schemas.chat import ChatIntent


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
    normalized = text.strip().lower()

    for category, label, keywords in KEYWORD_RULES:
        if any(keyword in normalized for keyword in keywords):
            return ChatIntent(category=category, label=label)

    return ChatIntent(category="summary", label="summary")
